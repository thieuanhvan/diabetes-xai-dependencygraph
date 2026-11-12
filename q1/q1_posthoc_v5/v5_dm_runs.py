"""POST HOC (S-P5), matched three-disease comparison: NHANES diabetes model, cohort and DiCE runs (plan Section 6).

Code path copied from the frozen HTN runner (q1_domain_htn/a2_htn_runs.py): P4 split (80/20, stratified, seed 42),
P4 XGBoost configuration, P4 DiCERunner per query (DiCE random, 5 counterfactuals, proximity/diversity weights of P4),
P7 cohort rule (p >= 0.5, at most the 200 highest-risk, floor 50), lock = {GenHlth, MentHlth}, rule R-IMM
(Income, Education, AnyHealthcare immutable in every mode; HighBP, KidneyDisease, Cycle immutable). Only DiCE random
in published and lock modes is run (no graph mode is needed for the comparison).

Variants:
  dm_a1c           label DM_A1C (HbA1c >= 6.5 %), HighBP = BPQ020 told (immutable)      (primary)
  dm_diag          label DM_DIAG (DIQ010 = 1), HighBP = BPQ020 told (immutable)         (secondary, refit)
  dm_hbp_measured  label DM_A1C, HighBP = mean SBP >= 130 mmHg (CKD definition, treatable) (secondary, refit)
Usage (P4 venv): python -I v5_dm_runs.py --variant dm_a1c
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
TOOLS = HERE.parent
for p in (str(TOOLS / "q1_domain_htn"), str(TOOLS / "q1_domain_ckd"), str(TOOLS / "crossdataset_p4")):
    if p not in sys.path:
        sys.path.insert(0, p)
warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import p7_cross_p4pipeline as P  # noqa: E402
import p7_cross_exhaustive as EX  # noqa: E402
from p7_cross_p4pipeline import CFG, FT, FeatureSpec, Mutability  # noqa: E402
from htn_common import PAPER7, below_normal, check_prereg, sha256_file, write_json  # noqa: E402

PLAN = PAPER7 / "prereg" / "posthoc_v5_plan_en_v1_20261112_1211.md"
PLAN_SHA256 = open(HERE / "PLAN_SHA256.txt", encoding="utf-8").read().split()[0]
OUT = PAPER7 / "outputs" / "q1_posthoc_v5" / "nhanes_dm"
SEEDS = [42, 123, 2024, 7, 31337]
N_WANTED = int(CFG["dice"]["n_counterfactuals"])
DESIRED = int(CFG["dice"]["desired_class"])
COHORT_MAX, COHORT_FLOOR = 200, 50
RIMM = ["Income", "Education", "AnyHealthcare"]
LOCK = ["GenHlth", "MentHlth"]
VARIANTS = {"dm_a1c": ("DM_A1C", "told"), "dm_diag": ("DM_DIAG", "told"), "dm_hbp_measured": ("DM_A1C", "measured")}


def roles(hbp):
    tab = pd.read_csv(OUT / "dm_role_table.csv")
    role = dict(zip(tab.variable, tab.role))
    if hbp == "measured":
        role["HighBP"] = "treatable"  # CKD definition: measured state, BLOOD_PRESSURE concept, diabetes role treatable
    return list(tab.variable), role


def patch_taxonomy(hbp):
    s = FT.FEATURE_TAXONOMY["Income"]
    FT.FEATURE_TAXONOMY["Income"] = FeatureSpec("Income", s.mutability, (1, 5), s.semantic_label + " [range patched]")
    for f, lab in (("KidneyDisease", "KIQ022 = 1"), ("Cycle", "NHANES cycle")):
        FT.FEATURE_TAXONOMY[f] = FeatureSpec(f, Mutability.IMMUTABLE, (0, 1), f"{lab} [DM domain]")
    if hbp == "told":
        s = FT.FEATURE_TAXONOMY["HighBP"]
        FT.FEATURE_TAXONOMY["HighBP"] = FeatureSpec("HighBP", Mutability.IMMUTABLE, s.value_range,
                                                    "BPQ020 told high BP [DM domain, diagnosis history]")
    for f in RIMM:
        s = FT.FEATURE_TAXONOMY[f]
        FT.FEATURE_TAXONOMY[f] = FeatureSpec(f, Mutability.IMMUTABLE, s.value_range, s.semantic_label + " [R-IMM]")


class Lock:
    def __enter__(self):
        self.saved = {f: FT.FEATURE_TAXONOMY[f] for f in LOCK}
        for f, s in self.saved.items():
            FT.FEATURE_TAXONOMY[f] = FeatureSpec(f, Mutability.IMMUTABLE, s.value_range, s.semantic_label)

    def __exit__(self, *a):
        for f, s in self.saved.items():
            FT.FEATURE_TAXONOMY[f] = s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=list(VARIANTS), required=True)
    a = ap.parse_args()
    check_prereg()
    if sha256_file(PLAN) != PLAN_SHA256:
        sys.exit("S-P5 plan hash mismatch")
    if "OMP_NUM_THREADS" in os.environ:
        sys.exit("OMP_NUM_THREADS is set; unset it (B-E3)")
    below_normal()
    a0 = json.loads((OUT / "a0_dm.json").read_text(encoding="utf-8"))
    for key, p in (("rows_csv_sha256", OUT / "nhanes_dm_rows_2017-2023.csv"), ("role_table_sha256", OUT / "dm_role_table.csv"),
                   ("lock_set_sha256", OUT / "dm_lock_set.txt")):
        if sha256_file(p) != a0[key]:
            sys.exit(f"hash mismatch: {p}")
    t_start = time.time()
    target, hbp = VARIANTS[a.variant]
    FEATS, ROLE = roles(hbp)
    INDS = {f for f, r in ROLE.items() if r == "indicator"}
    patch_taxonomy(hbp)
    out = OUT / f"runs_{a.variant}"
    out.mkdir(parents=True, exist_ok=True)

    d = pd.read_csv(OUT / "nhanes_dm_rows_2017-2023.csv")
    if hbp == "measured":
        d["HighBP"] = d["HighBP_measured"]
    n0 = len(d)
    d = d[d[target].notna()]
    n_lab = len(d)
    d = d[d[FEATS].notna().all(axis=1)].reset_index(drop=True)
    flow = {"rows_age_exam_notpregnant_any_label": n0, "label_available": n_lab, "complete_cases": len(d),
            "positive": int((d[target] == 1).sum()), "prevalence": float((d[target] == 1).mean()),
            "by_cycle": {int(c): {"n": int((d.Cycle == c).sum()), "positive": int(((d.Cycle == c) & (d[target] == 1)).sum())}
                         for c in (0, 1)}}
    X = d[FEATS].astype(float)
    y = d[target].astype(int)
    P.seed_everything(CFG["random"]["seed"])
    Xtr, Xte, ytr, yte = P.get_train_test_split(X, y, test_size=CFG["split"]["test_size"],
                                                seed=CFG["random"]["seed"], stratify=CFG["split"]["stratify"])
    res = P.train_xgb(Xtr, ytr, Xte, yte, P.XGBConfig(**CFG["xgboost"]))
    model, proba = res["model"], np.asarray(res["proba"])
    from sklearn.metrics import roc_auc_score
    auc = float(roc_auc_score(yte, proba))
    model.save_model(str(out / "xgb_dm.json"))
    pd.DataFrame({"row": Xte.index, "SEQN": d.loc[Xte.index, "SEQN"].values, "y": yte.values, "proba": proba}).to_csv(
        out / "test_proba.csv", index=False, float_format="%.10f")
    elig = np.where(proba >= 0.5)[0]
    idx = elig[np.argsort(proba[elig])][-min(COHORT_MAX, len(elig)):]
    queries = Xte.iloc[idx].copy()
    rows_idx = queries.index.to_numpy()
    queries = queries.reset_index(drop=True)
    cohort = pd.DataFrame({"pid": range(len(queries)), "row": rows_idx, "SEQN": d.loc[rows_idx, "SEQN"].values,
                           "proba": proba[idx], "label": d.loc[rows_idx, target].values,
                           "Cycle": d.loc[rows_idx, "Cycle"].values})
    pd.concat([cohort, queries.add_prefix("x_")], axis=1).to_csv(out / "cohort.csv", index=False)
    info = {"label": "POST HOC (S-P5), exploratory", "plan_sha256": PLAN_SHA256, "variant": a.variant, "target": target,
            "highbp": hbp, "roles": ROLE, "written": datetime.now().strftime("%d/%m/%Y %H:%M"), "flow": flow,
            "n_train": int(len(Xtr)), "n_test": int(len(Xte)), "test_auc": auc, "eligible_p_ge_0.5": int(len(elig)),
            "cohort_n": int(len(queries)), "cohort_min_proba": float(proba[idx].min()) if len(idx) else None,
            "features_in_model_order": FEATS, "lock_set": LOCK, "r_imm_applied": True, "xgboost": CFG["xgboost"],
            "seeds": SEEDS, "n_requested_per_patient_seed": N_WANTED}
    if len(queries) < COHORT_FLOOR:
        info["status"] = f"NOT REACHED: {len(queries)} < {COHORT_FLOOR} patients with p >= 0.5"
        write_json(out / "run_info.json", info)
        print(info["status"])
        return

    mov_rows, s1 = [], []
    for i in range(len(queries)):
        q = queries.iloc[i]
        ftv = FT.get_features_to_vary_for_query(q)
        perm = FT.get_permitted_range_for_query(q)
        movable = [f for f in ftv if f in FEATS and len(EX.grid(f, float(q[f]), perm[f]))]
        mov_rows.append({"pid": i, "movable": ";".join(movable), "n_movable": len(movable),
                         "n_ind_movable": sum(f in INDS for f in movable)})
        flip = False
        base = q[FEATS].to_numpy(dtype=float)
        for f in movable:
            if f in INDS:
                continue
            g = EX.grid(f, float(q[f]), perm[f])
            Xg = np.repeat(base[None, :], len(g), axis=0)
            Xg[:, FEATS.index(f)] = g
            if (model.predict(Xg) == DESIRED).any():
                flip = True
                break
        s1.append(flip)
    mov = pd.DataFrame(mov_rows)
    mov["single_nonindicator_flip"] = s1
    mov.to_csv(out / "movability.csv", index=False)
    info["pre_generator_single_nonindicator_flip_share"] = float(np.mean(s1))
    write_json(out / "run_info.json", info)
    print(f"[{a.variant}] n={len(d)} prev={flow['prevalence']:.4f} AUC={auc:.4f} eligible={len(elig)} "
          f"cohort={len(queries)} S1={np.mean(s1):.4f}", flush=True)

    spans = {f: max(FT.FEATURE_TAXONOMY[f].value_range[1] - FT.FEATURE_TAXONOMY[f].value_range[0], 1e-9) for f in FEATS}
    discrete = set(FT.get_discrete_features()) & set(FEATS)
    TGT = "DM_label"

    def changes_of(q, row):
        return [f for f in FEATS if ((int(round(float(q[f]))) != int(round(float(row[f])))) if f in discrete
                                     else abs(float(q[f]) - float(row[f])) > 1e-6)]

    def clean(cfs):
        dd = cfs.drop(columns=[TGT]) if TGT in cfs.columns else cfs.copy()
        for c in discrete:
            if c in dd.columns:
                dd[c] = dd[c].round().astype(int)
        return dd[FEATS]

    for mode in ("published", "lock"):
        for seed in SEEDS:
            fo = out / f"dice_{mode}_seed{seed}.csv"
            if fo.exists():
                continue
            t0 = time.time()
            recs, status = [], []
            ctx = Lock() if mode == "lock" else None
            if ctx:
                ctx.__enter__()
            try:
                R = P.DiCERunner(model=model, X_train=Xtr, y_train=ytr.rename(TGT), target_col=TGT,
                                 config=P.DiCEConfig(method="random", n_counterfactuals=N_WANTED, desired_class=DESIRED,
                                                     proximity_weight=CFG["dice"]["proximity_weight"],
                                                     diversity_weight=CFG["dice"]["diversity_weight"], per_query=True))
                P.seed_everything(seed)
                cfe = R.generate(queries)
                for i in range(len(queries)):
                    obj = cfe[i]
                    cfs = obj.final_cfs_df if obj is not None else None
                    if cfs is None or len(cfs) == 0:
                        status.append({"pid": i, "returned": 0, "rounds": 1})
                        continue
                    dd = clean(cfs)
                    pr = model.predict(dd.values)
                    for k in range(len(dd)):
                        q = queries.iloc[i]
                        chg = changes_of(q, dd.iloc[k])
                        rec = {"generator": "dice_random", "mode": mode, "seed": seed, "pid": i, "round": 1,
                               "valid": int(pr[k] == DESIRED), "changed": ";".join(chg), "n_changes": len(chg),
                               "dist": float(sum(abs(float(dd.iloc[k][f]) - float(q[f])) / spans[f] for f in chg))}
                        rec.update({f"cf_{f}": float(dd.iloc[k][f]) for f in FEATS})
                        recs.append(rec)
                    status.append({"pid": i, "returned": len(dd), "rounds": 1})
            finally:
                if ctx:
                    ctx.__exit__()
            pd.DataFrame(status).to_csv(out / f"dice_{mode}_seed{seed}_status.csv", index=False)
            pd.DataFrame(recs).to_csv(fo, index=False)
            print(f"[{a.variant}] dice {mode} seed {seed}: {len(recs)} CFs, {round(time.time() - t0)} s", flush=True)
    info["total_secs"] = round(time.time() - t_start)
    info["finished"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    write_json(out / "run_info.json", info)


if __name__ == "__main__":
    main()
