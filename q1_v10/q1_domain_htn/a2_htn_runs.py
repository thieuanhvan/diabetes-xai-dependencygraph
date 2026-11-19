"""P7 Q1 step A2-HTN: model, cohort and counterfactual runs (addendum HTN v3, Sections 3, 4, 6, 7).

Same code path as the frozen CKD a2_ckd_runs.py (P4 split, P4 XGBoost configuration, P4 DiCERunner per-query,
P7 regeneration rule, P7 exhaustive search with the value-returning copy checked against it); domain inputs are
the frozen A0-HTN files and the A1-HTN agreed AHA/ACC graph.

In-memory taxonomy (addendum 3, 6): Income range (1, 5); Diabetes, KidneyDisease, Cycle immutable (0, 1);
rule R-IMM: Income, Education, AnyHealthcare immutable in every mode (variant rimm_off = CKD-comparable reading,
P4 direction monotonic up kept). Lock = {GenHlth, MentHlth}. Route-aware primary: AHA/ACC, k = 1, all strengths.

Variants:
  main          L1, all analytic rows                                 (primary)
  less_exposed  same fitted model; cohort without BPQ020 = 1          (secondary)
  rimm_off      same fitted model and cohort; R-IMM not applied        (secondary, H1 under both readings)
  l2            refit on L2                                            (secondary)
  no_bpmed      refit without participants now taking BP medication   (secondary)
  no_dx         refit without Diabetes, KidneyDisease, Stroke, HeartDiseaseorAttack (secondary)
Usage (P7 venv, isolated): python -I a2_htn_runs.py --variant main [--parts dice,exh]
"""
from __future__ import annotations

import argparse
import itertools
import os
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
for p in (str(HERE), str(HERE.parent / "q1_domain_ckd"), str(HERE.parent / "crossdataset_p4")):
    if p not in sys.path:
        sys.path.insert(0, p)
warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import p7_cross_p4pipeline as P  # noqa: E402
import p7_cross_exhaustive as EX  # noqa: E402
from p7_cross_p4pipeline import CFG, FT, FeatureSpec, Mutability  # noqa: E402
import a2_domain_htn as D  # noqa: E402
from htn_common import check_prereg, sha256_file, write_json  # noqa: E402

SEEDS = [42, 123, 2024, 7, 31337]
MAX_ROUNDS = 8
N_WANTED = int(CFG["dice"]["n_counterfactuals"])
DESIRED = int(CFG["dice"]["desired_class"])
COHORT_MAX, COHORT_FLOOR = 200, 50
DX = ["Diabetes", "KidneyDisease", "Stroke", "HeartDiseaseorAttack"]
RIMM = ["Income", "Education", "AnyHealthcare"]
VARIANTS = {"main": ("HTN_L1_measured", None, False), "less_exposed": ("HTN_L1_measured", None, False),
            "rimm_off": ("HTN_L1_measured", None, False), "l2": ("HTN_L2_measured_or_treated", None, True),
            "no_bpmed": ("HTN_L1_measured", "no_bpmed", True), "no_dx": ("HTN_L1_measured", None, True)}


def patch_taxonomy(rimm: bool):
    s = FT.FEATURE_TAXONOMY["Income"]
    FT.FEATURE_TAXONOMY["Income"] = FeatureSpec("Income", s.mutability, (1, 5), s.semantic_label + " [range patched]")
    for f, lab in (("Diabetes", "DIQ010 = 1"), ("KidneyDisease", "KIQ022 = 1"), ("Cycle", "NHANES cycle")):
        FT.FEATURE_TAXONOMY[f] = FeatureSpec(f, Mutability.IMMUTABLE, (0, 1), f"{lab} [HTN domain]")
    if rimm:
        for f in RIMM:
            s = FT.FEATURE_TAXONOMY[f]
            FT.FEATURE_TAXONOMY[f] = FeatureSpec(f, Mutability.IMMUTABLE, s.value_range, s.semantic_label + " [R-IMM]")


class Lock:
    def __enter__(self):
        self.saved = {f: FT.FEATURE_TAXONOMY[f] for f in D.LOCK}
        for f, s in self.saved.items():
            FT.FEATURE_TAXONOMY[f] = FeatureSpec(f, Mutability.IMMUTABLE, s.value_range, s.semantic_label)

    def __exit__(self, *a):
        for f, s in self.saved.items():
            FT.FEATURE_TAXONOMY[f] = s


def search_full(model, q, cols, set_ok=None, row_ok=None):
    """Value-returning copy of p7_cross_exhaustive.search (as the frozen CKD copy)."""
    ftv = FT.get_features_to_vary_for_query(q)
    perm = FT.get_permitted_range_for_query(q)
    span = {f: max(FT.FEATURE_TAXONOMY[f].value_range[1] - FT.FEATURE_TAXONOMY[f].value_range[0], 1e-9) for f in ftv}
    cand = {f: EX.grid(f, float(q[f]), perm[f]) for f in ftv}
    ftv = [f for f in ftv if len(cand[f])]
    base = q[cols].to_numpy(dtype=float)
    pos = {c: j for j, c in enumerate(cols)}
    best = {}
    for k in range(1, EX.K_MAX + 1):
        for S in itertools.combinations(ftv, k):
            if set_ok is not None and not set_ok(S):
                continue
            prod = np.array(list(itertools.product(*[cand[f] for f in S])), dtype=float)
            X = np.repeat(base[None, :], len(prod), axis=0)
            for j, f in enumerate(S):
                X[:, pos[f]] = prod[:, j]
            ok = model.predict(X) == DESIRED
            if row_ok is not None and ok.any():
                ok = ok & np.array([row_ok(S, prod[r]) for r in range(len(prod))])
            if not ok.any():
                continue
            d = sum(np.abs(prod[:, j] - float(q[f])) / span[f] for j, f in enumerate(S))
            d[~ok] = np.inf
            i = int(np.argmin(d))
            best[frozenset(S)] = (k, float(d[i]), X[i].copy())
        if len(best) >= N_WANTED:
            break
    ranked = sorted(best.items(), key=lambda kv: (kv[1][0], kv[1][1], sorted(kv[0])))[:N_WANTED]
    return [(sorted(S), v[0], v[1], v[2]) for S, v in ranked]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=list(VARIANTS), required=True)
    ap.add_argument("--parts", default="dice,exh")
    a = ap.parse_args()
    check_prereg()
    t_start = time.time()
    for p, h in [(D.ANALYTIC, D.ANALYTIC_SHA256), (D.ROLE_TABLE, D.ROLE_TABLE_SHA256), (D.LOCK_SET, D.LOCK_SET_SHA256)]:
        if sha256_file(p) != h:
            sys.exit(f"hash mismatch: {p}")
    target, rowfilter, refit = VARIANTS[a.variant]
    patch_taxonomy(rimm=(a.variant != "rimm_off"))
    FEATS = [f for f in D.FEATURES if not (a.variant == "no_dx" and f in DX)]
    out = D.OUT / f"a2_runs_{a.variant}"
    out.mkdir(parents=True, exist_ok=True)
    mdir = D.OUT / ("a2_model" if not refit else f"a2_model_{a.variant}")
    mdir.mkdir(parents=True, exist_ok=True)

    d = pd.read_csv(D.ANALYTIC)
    d = d[d[target].notna()]
    if rowfilter == "no_bpmed":
        d = d[d["BP_med_now"].fillna(0) != 1]
    d = d.reset_index(drop=True) if a.variant in ("l2", "no_bpmed") else d
    X = d[FEATS].astype(float)
    y = d[target].astype(int)
    P.seed_everything(CFG["random"]["seed"])
    Xtr, Xte, ytr, yte = P.get_train_test_split(X, y, test_size=CFG["split"]["test_size"],
                                                seed=CFG["random"]["seed"], stratify=CFG["split"]["stratify"])
    res = P.train_xgb(Xtr, ytr, Xte, yte, P.XGBConfig(**CFG["xgboost"]))
    model, proba = res["model"], np.asarray(res["proba"])
    from sklearn.metrics import roc_auc_score
    auc = float(roc_auc_score(yte, proba))
    pfile = mdir / "test_proba.csv"
    tp = pd.DataFrame({"row": Xte.index, "SEQN": d.loc[Xte.index, "SEQN"].values, "y": yte.values, "proba": proba})
    if a.variant in ("less_exposed", "rimm_off"):
        ref = pd.read_csv(pfile)
        if not (np.array_equal(ref["row"].values, tp["row"].values)
                and np.allclose(ref["proba"].values, tp["proba"].values, atol=1e-9, rtol=0)):
            sys.exit("model refit differs from the main run")
    else:
        model.save_model(str(mdir / "xgb_htn.json"))
        tp.to_csv(pfile, index=False, float_format="%.10f")

    elig_mask = proba >= 0.5
    if a.variant == "less_exposed":
        elig_mask &= ~(d.loc[Xte.index, "BPQ020_toldHighBP"].fillna(0).values == 1)
    elig = np.where(elig_mask)[0]
    idx = elig[np.argsort(proba[elig])][-min(COHORT_MAX, len(elig)):]
    queries = Xte.iloc[idx].copy()
    rows_idx = queries.index.to_numpy()
    queries = queries.reset_index(drop=True)
    cohort = pd.DataFrame({"pid": range(len(queries)), "row": rows_idx, "SEQN": d.loc[rows_idx, "SEQN"].values,
                           "proba": proba[idx], "label": d.loc[rows_idx, target].values,
                           "L1": d.loc[rows_idx, "HTN_L1_measured"].values,
                           "BPQ020": d.loc[rows_idx, "BPQ020_toldHighBP"].values,
                           "Cycle": d.loc[rows_idx, "Cycle"].values})
    cohort = pd.concat([cohort, queries.add_prefix("x_")], axis=1)
    cohort.to_csv(out / "cohort.csv", index=False)
    AE = D.aha_edges()
    GRAPH = D.AGREEMENT.exists()  # False: agreed graph not reached (recall gate failed); route/capped modes not run
    info = {"variant": a.variant, "target": target, "written": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "n_analytic": int(len(d)), "n_train": int(len(Xtr)), "n_test": int(len(Xte)), "test_auc": auc,
            "eligible_p_ge_0.5": int(len(elig)), "cohort_n": int(len(queries)),
            "cohort_min_proba": float(proba[idx].min()) if len(idx) else None,
            "features_in_model_order": FEATS, "lock_set": D.LOCK, "r_imm_applied": a.variant != "rimm_off",
            "xgboost": CFG["xgboost"], "seeds": SEEDS, "max_rounds": MAX_ROUNDS, "n_requested_per_patient_seed": N_WANTED,
            "aha_agreed_graph": "available" if GRAPH else "not reached (extractor B failed the recall gate)", "aha_edges": AE, "kdigo_edges": D.kdigo_edges(), "ada_edges": D.ada_edges()}
    if len(queries) < COHORT_FLOOR:
        info["status"] = f"NOT REACHED: {len(queries)} < {COHORT_FLOOR} patients with p >= 0.5"
        write_json(out / "run_info.json", info)
        print(info["status"])
        return

    E = D.edge_set(AE)
    INDS = D.INDICATORS
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
    sup_levers = sorted({u for (u, v) in E if v in INDS and D.ROLE.get(u) == "lever"})
    shares = {u: float(np.mean([u in m.split(";") for m in mov["movable"]])) for u in sup_levers}
    info["near_degenerate_check"] = {
        "supporting_levers_aha_k1": sup_levers, "share_cohort_movable": shares,
        "rule": "near-degenerate iff every supporting lever is movable for < 10% of cohort patients (addendum 7.3)",
        "near_degenerate": bool(sup_levers) and all(s < 0.10 for s in shares.values()),
        "degenerate": not any(v in INDS for (_, v) in E),
        "status": "computed" if GRAPH else "not reached (no agreed graph)"}
    info["pre_generator_single_nonindicator_flip_share"] = float(np.mean(s1))
    write_json(out / "run_info.json", info)
    print(f"[{a.variant}] AUC={auc:.4f} eligible={len(elig)} cohort={len(queries)} nd={info['near_degenerate_check']} "
          f"S1={np.mean(s1):.4f}", flush=True)

    spans = {f: max(FT.FEATURE_TAXONOMY[f].value_range[1] - FT.FEATURE_TAXONOMY[f].value_range[0], 1e-9) for f in FEATS}
    discrete = set(FT.get_discrete_features()) & set(FEATS)
    TGT = "HTN_label"

    def changes_of(q, row):
        outc = []
        for f in FEATS:
            b, c = float(q[f]), float(row[f])
            if ((int(round(b)) != int(round(c))) if f in discrete else abs(b - c) > 1e-6):
                outc.append(f)
        return outc

    def dist_of(q, row, chg):
        return float(sum(abs(float(row[f]) - float(q[f])) / spans[f] for f in chg))

    def clean(cfs):
        dd = cfs.drop(columns=[TGT]) if TGT in cfs.columns else cfs.copy()
        for c in discrete:
            if c in dd.columns:
                dd[c] = dd[c].round().astype(int)
        return dd[FEATS]

    def runner():
        return P.DiCERunner(model=model, X_train=Xtr, y_train=ytr.rename(TGT), target_col=TGT,
                            config=P.DiCEConfig(method="random", n_counterfactuals=N_WANTED, desired_class=DESIRED,
                                                proximity_weight=CFG["dice"]["proximity_weight"],
                                                diversity_weight=CFG["dice"]["diversity_weight"], per_query=True))

    def cf_record(mode, seed, i, rnd, row, valid, chg, gen):
        rec = {"generator": gen, "mode": mode, "seed": seed, "pid": i, "round": rnd, "valid": int(valid),
               "changed": ";".join(chg), "n_changes": len(chg), "dist": dist_of(queries.iloc[i], row, chg)}
        rec.update({f"cf_{f}": float(row[f]) for f in FEATS})
        return rec

    if "dice" in a.parts:
        for mode in (("published", "lock", "route") if GRAPH else ("published", "lock")):
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
                    R = runner()
                    if mode in ("published", "lock"):
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
                                recs.append(cf_record(mode, seed, i, 1, dd.iloc[k], pr[k] == DESIRED,
                                                      changes_of(queries.iloc[i], dd.iloc[k]), "dice_random"))
                            status.append({"pid": i, "returned": len(dd), "rounds": 1})
                    else:
                        for i in range(len(queries)):
                            q = queries.iloc[i]
                            kept, r = [], 0
                            while len(kept) < N_WANTED and r < MAX_ROUNDS:
                                r += 1
                                P.seed_everything(seed + 100_000 * r)
                                obj = R.generate(queries.iloc[[i]].reset_index(drop=True))[0]
                                cfs = obj.final_cfs_df if obj is not None else None
                                if cfs is None or len(cfs) == 0:
                                    continue
                                dd = clean(cfs)
                                for k in range(len(dd)):
                                    if len(kept) >= N_WANTED:
                                        break
                                    chg = changes_of(q, dd.iloc[k])
                                    if D.accept(chg, E, 1, False):
                                        kept.append((r, dd.iloc[k], chg))
                            if kept:
                                dk = pd.DataFrame([x[1] for x in kept])
                                pr = model.predict(dk[FEATS].values)
                                for (rr, row, chg), pv in zip(kept, pr):
                                    recs.append(cf_record(mode, seed, i, rr, row, pv == DESIRED, chg, "dice_random"))
                            status.append({"pid": i, "returned": len(kept), "rounds": r})
                finally:
                    if ctx:
                        ctx.__exit__()
                pd.DataFrame(status).to_csv(out / f"dice_{mode}_seed{seed}_status.csv", index=False)
                pd.DataFrame(recs).to_csv(fo, index=False)
                print(f"[{a.variant}] dice {mode} seed {seed}: {len(recs)} CFs, {round(time.time() - t0)} s", flush=True)

    if "exh" in a.parts:
        fo = out / "exhaustive.csv"
        if not fo.exists():
            t0 = time.time()
            P.admissible = lambda chg: D.accept(chg, E, 1, False)
            recs, mism = [], 0
            for mode in (("published", "lock", "route", "capped") if GRAPH else ("published", "lock")):
                ctx = Lock() if mode == "lock" else None
                if ctx:
                    ctx.__enter__()
                try:
                    for i in range(len(queries)):
                        q = queries.iloc[i]
                        if mode == "capped":
                            before = {f: float(q[f]) for f in FEATS}

                            def row_ok(S, vals, before=before):
                                after = dict(before)
                                after.update(dict(zip(S, vals)))
                                return D.capped_ok(set(S), before, after, E)
                            mine = search_full(model, q, FEATS, set_ok=lambda S: D.accept(S, E, 1, False), row_ok=row_ok)
                        else:
                            p7 = EX.search(model, q, FEATS, "route_A" if mode == "route" else mode)
                            mine = search_full(model, q, FEATS,
                                               set_ok=(lambda S: D.accept(S, E, 1, False)) if mode == "route" else None)
                            if [(s, k, dd) for s, k, dd, _ in mine] != p7:
                                mism += 1
                        for rank, (S, k, dist, vals) in enumerate(mine):
                            row = pd.Series(vals, index=FEATS)
                            recs.append(cf_record(mode, 0, i, rank, row, True, S, "exhaustive") | {"n_changes": k, "dist": dist})
                finally:
                    if ctx:
                        ctx.__exit__()
                print(f"[{a.variant}] exhaustive {mode} done, {round(time.time() - t0)} s", flush=True)
            if mism:
                sys.exit(f"value-returning search differs from P7 search on {mism} patient-modes: bug, stop")
            pd.DataFrame(recs).to_csv(fo, index=False)
            info["exhaustive_parity_with_p7_search"] = "identical on every patient and mode run (published, lock" + (", route)" if GRAPH else ")")
    info["total_secs"] = round(time.time() - t_start)
    info["finished"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    write_json(out / "run_info.json", info)


if __name__ == "__main__":
    main()
