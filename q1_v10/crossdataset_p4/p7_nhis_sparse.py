"""Sparse headroom: DiCE 'random' searches 1-feature changes first, then 2, ...
For each cohort patient: can ONE feature change flip the prediction? Which tier supplies it?
Can TWO non-indicator features flip it?  Same model/cohort as the cross-dataset runner."""
import sys, itertools, importlib
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import p7_cross_p4pipeline as X
IND = {"GenHlth", "PhysHlth", "MentHlth"}

def values(FT, f, q):
    lo, hi = FT.FEATURE_TAXONOMY[f].value_range
    m = FT._effective_mutability(FT.FEATURE_TAXONOMY[f])
    cur = float(q[f])
    grid = np.arange(np.floor(lo), np.ceil(hi) + 1e-9, 1.0)
    if f == "BMI":
        grid = np.arange(lo, hi + 1e-9, 1.0)
        return [v for v in grid if abs(v - cur) > 1e-9]
    if m == X.Mutability.MONOTONIC_UP:
        return [v for v in grid if v > cur]
    if m == X.Mutability.MONOTONIC_DOWN:
        return [v for v in grid if v < cur]
    return [v for v in grid if v != cur]

rows = []
for ds in ["brfss2021", "nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c",
           "nhanes2021-2023_diag", "nhanes2021-2023_a1c"]:
    importlib.reload(X.FT); FT = X.FT
    X.seed_everything(X.CFG["random"]["seed"])
    Xd, y, rb = X.load(ds)
    Xtr, Xte, ytr, yte = X.get_train_test_split(Xd, y, test_size=0.2, seed=42, stratify=True)
    res = X.train_xgb(Xtr, ytr, Xte, yte, X.XGBConfig(**X.CFG["xgboost"]))
    model, proba = res["model"], np.asarray(res["proba"])
    elig = np.where(proba >= 0.5)[0]
    Q = Xte.iloc[elig[np.argsort(proba[elig])][-200:]].reset_index(drop=True)
    one_ind = one_non = two_non = 0
    share_flip_ind = []
    for i in range(len(Q)):
        q = Q.iloc[i]
        ftv = FT.get_features_to_vary_for_query(q)
        singles = {}
        cands, owners = [], []
        for f in ftv:
            for v in values(FT, f, q):
                z = q.copy(); z[f] = v; cands.append(z.values); owners.append(f)
        if cands:
            p = model.predict_proba(np.array(cands))[:, 1]
            flipped = {owners[k] for k in range(len(owners)) if p[k] < 0.5}
            one_ind += bool(flipped & IND); one_non += bool(flipped - IND)
            share_flip_ind.append(len(flipped & IND) / max(len(flipped), 1) if flipped else np.nan)
        non = [f for f in ftv if f not in IND]
        ok = False
        for f1, f2 in itertools.combinations(non, 2):
            c2 = [q.copy() for _ in range(0)]
            grid = [(v1, v2) for v1 in values(FT, f1, q) for v2 in values(FT, f2, q)]
            if not grid: continue
            A = np.repeat(q.values[None, :], len(grid), axis=0)
            j1, j2 = list(Q.columns).index(f1), list(Q.columns).index(f2)
            A[:, j1] = [g[0] for g in grid]; A[:, j2] = [g[1] for g in grid]
            if (model.predict_proba(A)[:, 1] < 0.5).any():
                ok = True; break
        two_non += ok
    n = len(Q)
    rows.append({"dataset": ds, "cohort": n, "one_change_via_indicator": one_ind / n,
                 "one_change_via_non_indicator": one_non / n, "two_changes_non_indicator": two_non / n,
                 "share_of_single_flips_that_are_indicators": float(np.nanmean(share_flip_ind))})
    print(rows[-1], flush=True)
out = pd.DataFrame(rows)
out.to_csv(Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4") / "nhis_sparse_headroom.csv", index=False)
print(out.round(3).to_string(index=False))
