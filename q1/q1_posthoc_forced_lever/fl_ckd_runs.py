"""POST HOC (S-P4), exploratory: CKD lock plus forced lever (plan Section 5), graph-free analogue of the CKD
route-aware mode. Plan: prereg/posthoc_forced_lever_plan_en_v1_20261112_0957.md (hash checked).

The frozen A2 modules (a2_domain, a2_ckd_runs, p7_cross_p4pipeline, p7_cross_exhaustive) are imported unchanged.
  DiCE random, mode 'forced': generation under the CKD lock ({GenHlth, MentHlth} immutable); a returned
      counterfactual is accepted only when its change set contains a lever or treatable (D.LEVERS | D.TREATABLE);
      regeneration as the frozen route-aware rule (seed + 100,000 r, at most 8 rounds, 5 requested per seed).
  Exhaustive search, mode 'forced': frozen value-returning copy search_full under the lock with the set filter
      "contains a lever or treatable".
Configurations: --config ses_freeze (Education, Income, AnyHealthcare immutable in every mode, as S-P1) or
--config frozen (A2 as preregistered). The seed-42 refit must equal the frozen A2 test probabilities and the
rebuilt cohort must equal the saved cohort of that configuration; otherwise the script stops.

Usage (P4 venv): python -I fl_ckd_runs.py --config ses_freeze|frozen
Outputs: outputs/q1_posthoc_forced_lever/ckd_<config>/ dice_forced_seed<s>.csv (+ _status), exhaustive_forced.csv,
run_info.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
for p in (str(TOOLS / "q1_domain_ckd"), str(TOOLS / "crossdataset_p4")):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

PAPER7 = Path("D:/20-study/uit/research/diabetesxai/paper7")
PLAN = PAPER7 / "prereg" / "posthoc_forced_lever_plan_en_v1_20261112_0957.md"
PLAN_SHA256 = "b1c7624aea42fa4e7911e869db77e71f44ccbe9dc983416acaf53c214cdf87e0"
OUTROOT = PAPER7 / "outputs" / "q1_posthoc_forced_lever"
FROZEN_PROBA = PAPER7 / "outputs" / "q1_domain_ckd" / "a2_model" / "test_proba.csv"
REF_COHORT = {"frozen": PAPER7 / "outputs" / "q1_domain_ckd" / "a2_runs_main" / "cohort.csv",
              "ses_freeze": PAPER7 / "outputs" / "q1_posthoc_ses_splits" / "ses_freeze" / "a2_runs_main" / "cohort.csv"}
SES = ["Education", "Income", "AnyHealthcare"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", choices=["ses_freeze", "frozen"], required=True)
    a = ap.parse_args()
    if hashlib.sha256(PLAN.read_bytes()).hexdigest() != PLAN_SHA256:
        sys.exit("S-P4 plan hash mismatch")

    import a2_domain as D
    import a2_ckd_runs as R
    import p7_cross_p4pipeline as P
    from p7_cross_p4pipeline import CFG, FT, FeatureSpec, Mutability
    from q1_common import below_normal, check_prereg, sha256_file, write_json

    check_prereg()
    below_normal()
    for p, h in [(D.ANALYTIC, D.ANALYTIC_SHA256), (D.ROLE_TABLE, D.ROLE_TABLE_SHA256), (D.LOCK_SET, D.LOCK_SET_SHA256)]:
        if sha256_file(p) != h:
            sys.exit(f"hash mismatch: {p}")
    R.patch_taxonomy()
    if a.config == "ses_freeze":
        for f in SES:
            sp = FT.FEATURE_TAXONOMY[f]
            FT.FEATURE_TAXONOMY[f] = FeatureSpec(f, Mutability.IMMUTABLE, sp.value_range, sp.semantic_label + " [frozen post hoc]")
    out = OUTROOT / f"ckd_{a.config}"
    out.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    d = pd.read_csv(D.ANALYTIC)
    X = d[D.FEATURES].astype(float)
    y = d[R.TARGET].astype(int)
    P.seed_everything(CFG["random"]["seed"])
    Xtr, Xte, ytr, yte = P.get_train_test_split(X, y, test_size=CFG["split"]["test_size"],
                                                seed=CFG["random"]["seed"], stratify=CFG["split"]["stratify"])
    res = P.train_xgb(Xtr, ytr, Xte, yte, P.XGBConfig(**CFG["xgboost"]))
    model, proba = res["model"], np.asarray(res["proba"])
    ref = pd.read_csv(FROZEN_PROBA)
    if not np.allclose(ref["proba"].to_numpy(), proba, atol=1e-9, rtol=0):
        sys.exit("refit differs from the frozen A2 model: stop")
    elig = np.where(proba >= 0.5)[0]
    idx = elig[np.argsort(proba[elig])][-min(R.COHORT_MAX, len(elig)):]
    queries = Xte.iloc[idx].copy()
    rows_idx = queries.index.to_numpy()
    queries = queries.reset_index(drop=True)
    refc = pd.read_csv(REF_COHORT[a.config])
    if not np.array_equal(refc["row"].to_numpy(), rows_idx):
        sys.exit("rebuilt cohort differs from the saved cohort: stop")

    ACTION = set(D.LEVERS) | set(D.TREATABLE)
    discrete = set(FT.get_discrete_features()) & set(D.FEATURES)
    spans = {f: max(FT.FEATURE_TAXONOMY[f].value_range[1] - FT.FEATURE_TAXONOMY[f].value_range[0], 1e-9)
             for f in D.FEATURES}

    def changes_of(q, row):
        outc = []
        for f in D.FEATURES:
            b, c = float(q[f]), float(row[f])
            moved = (int(round(b)) != int(round(c))) if f in discrete else abs(b - c) > 1e-6
            if moved:
                outc.append(f)
        return outc

    def dist_of(q, row, chg):
        return float(sum(abs(float(row[f]) - float(q[f])) / spans[f] for f in chg))

    def clean(cfs):
        dd = cfs.drop(columns=[R.TARGET]) if R.TARGET in cfs.columns else cfs.copy()
        for c in discrete:
            if c in dd.columns:
                dd[c] = dd[c].round().astype(int)
        return dd[D.FEATURES]

    def accept(chg):
        return bool(set(chg) & ACTION)

    info = {"label": "POST HOC (S-P4), exploratory", "plan_sha256": PLAN_SHA256, "config": a.config,
            "ses_frozen": a.config == "ses_freeze", "cohort_n": int(len(queries)), "lock_set": D.LOCK,
            "action_features": sorted(ACTION), "seeds": R.SEEDS, "max_rounds": R.MAX_ROUNDS,
            "identity_refit_equals_frozen_A2": True, "cohort_equals_saved": True,
            "started": datetime.now().strftime("%d/%m/%Y %H:%M")}
    write_json(out / "run_info.json", info)

    lock = R.Lock()
    lock.__enter__()
    try:
        for seed in R.SEEDS:
            fo = out / f"dice_forced_seed{seed}.csv"
            if fo.exists():
                continue
            t0 = time.time()
            Rn = P.DiCERunner(model=model, X_train=Xtr, y_train=ytr, target_col=R.TARGET,
                              config=P.DiCEConfig(method="random", n_counterfactuals=R.N_WANTED, desired_class=R.DESIRED,
                                                  proximity_weight=CFG["dice"]["proximity_weight"],
                                                  diversity_weight=CFG["dice"]["diversity_weight"], per_query=True))
            recs, status = [], []
            for i in range(len(queries)):
                q = queries.iloc[i]
                kept, r = [], 0
                while len(kept) < R.N_WANTED and r < R.MAX_ROUNDS:
                    r += 1
                    P.seed_everything(seed + 100_000 * r)
                    obj = Rn.generate(queries.iloc[[i]].reset_index(drop=True))[0]
                    cfs = obj.final_cfs_df if obj is not None else None
                    if cfs is None or len(cfs) == 0:
                        continue
                    dd = clean(cfs)
                    for k in range(len(dd)):
                        if len(kept) >= R.N_WANTED:
                            break
                        chg = changes_of(q, dd.iloc[k])
                        if accept(chg):
                            kept.append((r, dd.iloc[k], chg))
                if kept:
                    dk = pd.DataFrame([x[1] for x in kept])
                    pr = model.predict(dk[D.FEATURES].values)
                    for (rr, row, chg), pv in zip(kept, pr):
                        rec = {"generator": "dice_random", "mode": "forced", "seed": seed, "pid": i, "round": rr,
                               "valid": int(pv == R.DESIRED), "changed": ";".join(chg), "n_changes": len(chg),
                               "dist": dist_of(q, row, chg)}
                        rec.update({f"cf_{f}": float(row[f]) for f in D.FEATURES})
                        recs.append(rec)
                status.append({"pid": i, "returned": len(kept), "rounds": r})
            pd.DataFrame(status).to_csv(out / f"dice_forced_seed{seed}_status.csv", index=False)
            pd.DataFrame(recs).to_csv(fo, index=False)
            print(f"[{a.config}] dice forced seed {seed}: {len(recs)} CFs, {round(time.time() - t0)} s", flush=True)

        fo = out / "exhaustive_forced.csv"
        if not fo.exists():
            t0 = time.time()
            recs = []
            for i in range(len(queries)):
                q = queries.iloc[i]
                mine = R.search_full(model, q, D.FEATURES, set_ok=lambda S: bool(set(S) & ACTION))
                for rank, (S, k, dist, vals) in enumerate(mine):
                    row = pd.Series(vals, index=D.FEATURES)
                    rec = {"generator": "exhaustive", "mode": "forced", "seed": 0, "pid": i, "round": rank, "valid": 1,
                           "changed": ";".join(S), "n_changes": k, "dist": dist}
                    rec.update({f"cf_{f}": float(row[f]) for f in D.FEATURES})
                    recs.append(rec)
            pd.DataFrame(recs).to_csv(fo, index=False)
            print(f"[{a.config}] exhaustive forced done, {round(time.time() - t0)} s", flush=True)
    finally:
        lock.__exit__()
    info["total_secs"] = round(time.time() - t_start)
    info["finished"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    write_json(out / "run_info.json", info)


if __name__ == "__main__":
    main()
