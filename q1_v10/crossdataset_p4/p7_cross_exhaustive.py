"""Third generator for the P7 journal version: exhaustive sparse search (no DiCE, deterministic).

Same data, split, XGBoost model, cohort (p >= 0.5, top 200) and P4 per-query constraints
(features_to_vary + permitted direction/range from the taxonomy) as p7_cross_p4pipeline.py.
For each patient, enumerate every change of 1, 2, then 3 permitted features over the integer grid
of their permitted range, keep the candidates that the model predicts as class 0, and for each
distinct set of changed features keep the closest candidate (L1 distance normalised by the
feature range). The 5 best sets, ranked by (number of changes, distance), are the counterfactuals.
Search stops at the smallest k that already gives 5 sets.

Modes: published (P4 constraints) | tableV (GenHlth, PhysHlth, MentHlth immutable)
       | route_A (only change sets admissible under the universal route reading; exact filter,
         no regeneration needed).
Every returned CF is valid by construction; the cost of enforcement shows up as patients with no
CF within 3 changes, more changes per CF, and larger distance.
"""
from __future__ import annotations
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # v10 shadow: python -I omits the script dir

import argparse
import itertools
import time

import numpy as np
import pandas as pd

import p7_cross_p4pipeline as P  # same loaders, taxonomy patches, admissible(), low priority
from p7_cross_p4pipeline import CFG, FT, FeatureSpec, Mutability, TABLE_V, TARGET, OUT
from depgraph.audit import summarise
from depgraph.nodes import TIER

K_MAX = 3
N_WANTED = P.N_WANTED


def grid(name, cur, rng):
    lo, hi = rng
    vals = np.arange(np.ceil(lo), np.floor(hi) + 1)
    return vals[vals != round(cur)]


def search(model, q, cols, mode):
    ftv = FT.get_features_to_vary_for_query(q)
    perm = FT.get_permitted_range_for_query(q)
    span = {f: max(FT.FEATURE_TAXONOMY[f].value_range[1] - FT.FEATURE_TAXONOMY[f].value_range[0], 1e-9) for f in ftv}
    cand = {f: grid(f, float(q[f]), perm[f]) for f in ftv}
    ftv = [f for f in ftv if len(cand[f])]
    base = q[cols].to_numpy(dtype=float)
    pos = {c: j for j, c in enumerate(cols)}
    best = {}  # frozenset(features) -> (dist, values)
    for k in range(1, K_MAX + 1):
        for S in itertools.combinations(ftv, k):
            if mode == "route_A" and not P.admissible(S):
                continue
            prod = np.array(list(itertools.product(*[cand[f] for f in S])), dtype=float)
            X = np.repeat(base[None, :], len(prod), axis=0)
            for j, f in enumerate(S):
                X[:, pos[f]] = prod[:, j]
            ok = model.predict(X) == CFG["dice"]["desired_class"]
            if not ok.any():
                continue
            d = sum(np.abs(prod[:, j] - float(q[f])) / span[f] for j, f in enumerate(S))
            d[~ok] = np.inf
            i = int(np.argmin(d))
            best[frozenset(S)] = (k, float(d[i]), X[i])
        if len(best) >= N_WANTED:
            break
    ranked = sorted(best.items(), key=lambda kv: (kv[1][0], kv[1][1], sorted(kv[0])))[:N_WANTED]
    return [(sorted(S), v[0], v[1]) for S, v in ranked]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--modes", default="published,tableV,route_A")
    ap.add_argument("--n", type=int, default=int(CFG["evaluate"]["n_test_instances"]))
    ap.add_argument("--tag", default="_exh")
    a = ap.parse_args()
    P.seed_everything(CFG["random"]["seed"])
    X, y, _ = P.load(a.dataset)
    Xtr, Xte, ytr, yte = P.get_train_test_split(X, y, test_size=CFG["split"]["test_size"],
                                                seed=CFG["random"]["seed"], stratify=CFG["split"]["stratify"])
    res = P.train_xgb(Xtr, ytr, Xte, yte, P.XGBConfig(**CFG["xgboost"]))
    model, proba = res["model"], np.asarray(res["proba"])
    from sklearn.metrics import roc_auc_score
    auc = roc_auc_score(yte, proba)
    elig = np.where(proba >= 0.5)[0]
    idx = elig[np.argsort(proba[elig])][-min(a.n, len(elig)):]
    queries = Xte.iloc[idx].reset_index(drop=True)
    cols = list(X.columns)
    print(f"{a.dataset}: AUC={auc:.4f} cohort={len(queries)} eligible={len(elig)}", flush=True)
    rows, per_cf_rows = [], []
    for mode in a.modes.split(","):
        t0 = time.time()
        saved = {f: FT.FEATURE_TAXONOMY[f] for f in TABLE_V}
        if mode == "tableV":
            for f, s in saved.items():
                FT.FEATURE_TAXONOMY[f] = FeatureSpec(f, Mutability.IMMUTABLE, s.value_range, s.semantic_label)
        per_cf, n_no, k_best, d_best = [], 0, [], []
        for i in range(len(queries)):
            out = search(model, queries.iloc[i], cols, mode)
            if not out:
                n_no += 1
                continue
            k_best.append(out[0][1])
            d_best.append(out[0][2])
            for S, k, dist in out:
                per_cf.append(S)
                per_cf_rows.append({"dataset": a.dataset, "mode": mode, "seed": 0, "pid": i, "valid": 1,
                                    "changed": ";".join(S), "n_changes": k, "dist": round(dist, 6)})
        for f, s in saved.items():
            FT.FEATURE_TAXONOMY[f] = s
        role = summarise(per_cf, reading="narrow", rule="role")
        edge = summarise(per_cf, reading="narrow", rule="edge")
        row = {"dataset": a.dataset, "method": "exhaustive", "mode": mode, "seed": 0, "auc": round(auc, 4),
               "cohort": len(queries), "eligible": len(elig), "n_cf": len(per_cf), "queries_with_no_cf": n_no,
               "coverage": 1 - n_no / len(queries), "best_k_mean": float(np.mean(k_best)) if k_best else np.nan,
               "best_dist_mean": float(np.mean(d_best)) if d_best else np.nan,
               "cf_touching_indicator": role["cf_touching_target"], "unsupported_edge_rule": edge["cf_unsupported"],
               "fully_unactionable": role["cf_fully_unactionable"], "secs": round(time.time() - t0)}
        rows.append(row)
        print(row, flush=True)
        pd.DataFrame(rows).to_csv(OUT / f"cross_{a.dataset}{a.tag}_summary.csv", index=False)
        pd.DataFrame(per_cf_rows).to_csv(OUT / f"cross_{a.dataset}{a.tag}_changes.csv", index=False)


if __name__ == "__main__":
    main()
