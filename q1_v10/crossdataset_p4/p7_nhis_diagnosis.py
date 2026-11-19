"""Why does enforcement cost validity on NHIS but not on BRFSS/NHANES?

Same model, split and cohort as p7_cross_p4pipeline.py (P4 pipeline, seed 42, p >= 0.5, top 200).
Three diagnostics per dataset:
 1. Headroom: share of the cohort whose predicted class flips (p < 0.5) when every
    feature DiCE may vary is set to its best permitted value (P4 taxonomy ranges/directions),
    (a) with indicators allowed (published search space), (b) without indicators (Table V).
    The gap (a) - (b) is how much recourse exists ONLY through indicators.
 2. Indicator reliance of the model: share of XGBoost total gain on indicator features.
 3. Search-space size: mean number of features DiCE may vary per query, with and without
    indicators, and which levers exist in the dataset.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p7_cross_p4pipeline as X  # noqa: E402  (re-uses load(), CFG, taxonomy, pipeline imports)

FT, Mut = X.FT, X.Mutability
IND = ["GenHlth", "PhysHlth", "MentHlth"]


def best_value(f, q):
    spec = FT.FEATURE_TAXONOMY[f]
    lo, hi = spec.value_range
    m = FT._effective_mutability(spec)
    if m == Mut.MONOTONIC_UP:
        return max(float(q[f]), hi)
    if m == Mut.MONOTONIC_DOWN:
        return min(float(q[f]), lo)
    return None  # bidirectional handled by search


def headroom(model, queries, allow_ind, bmi_grid):
    flips = 0
    nvary = []
    for i in range(len(queries)):
        q = queries.iloc[i]
        ftv = [f for f in FT.get_features_to_vary_for_query(q) if allow_ind or f not in IND]
        nvary.append(len(ftv))
        x = q.copy()
        for f in ftv:
            if f == "BMI":
                continue
            b = best_value(f, q)
            if b is not None:
                x[f] = b
        cands = []
        for v in (bmi_grid if "BMI" in ftv else [float(q["BMI"])]):
            y = x.copy()
            y["BMI"] = v
            cands.append(y)
        p = model.predict_proba(pd.DataFrame(cands)[queries.columns].values)[:, 1]
        flips += int((p < 0.5).any())
    return flips / len(queries), float(np.mean(nvary))


rows = []
for ds in ["brfss2021", "nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c",
           "nhanes2021-2023_diag", "nhanes2021-2023_a1c"]:
    # reset taxonomy patches between datasets
    import importlib
    importlib.reload(X.FT)
    X.FT = FT = importlib.import_module("src.pipelines.counterfactual.feature_taxonomy")
    X.seed_everything(X.CFG["random"]["seed"])
    Xd, y, round_bmi = X.load(ds)
    Xtr, Xte, ytr, yte = X.get_train_test_split(Xd, y, test_size=X.CFG["split"]["test_size"],
                                                seed=X.CFG["random"]["seed"], stratify=X.CFG["split"]["stratify"])
    res = X.train_xgb(Xtr, ytr, Xte, yte, X.XGBConfig(**X.CFG["xgboost"]))
    model, proba = res["model"], np.asarray(res["proba"])
    elig = np.where(proba >= 0.5)[0]
    idx = elig[np.argsort(proba[elig])][-200:]
    queries = Xte.iloc[idx].reset_index(drop=True)
    lo, hi = FT.FEATURE_TAXONOMY["BMI"].value_range
    grid = list(np.arange(lo, hi + 1e-9, 1.0)) if round_bmi or "nhanes" in ds or ds == "brfss2021" else list(np.arange(lo, hi + 1e-9, 0.5))
    h_all, nv_all = headroom(model, queries, True, grid)
    h_noind, nv_noind = headroom(model, queries, False, grid)
    g = pd.Series(model.get_booster().get_score(importance_type="total_gain"))
    names = list(Xd.columns)
    g.index = [names[int(k[1:])] if k.startswith("f") and k[1:].isdigit() else k for k in g.index]
    g = g / g.sum()
    levers = [f for f in names if X.TIER.get(f) == "lever"]
    rows.append({"dataset": ds, "cohort": len(queries), "headroom_with_ind": h_all, "headroom_no_ind": h_noind,
                 "only_via_indicators": h_all - h_noind, "n_vary_with_ind": nv_all, "n_vary_no_ind": nv_noind,
                 "gain_share_indicators": float(g.reindex(IND).fillna(0).sum()),
                 "gain_share_GenHlth": float(g.get("GenHlth", 0)), "gain_share_BMI": float(g.get("BMI", 0)),
                 "levers_present": ",".join(levers)})
    print(rows[-1], flush=True)
out = pd.DataFrame(rows)
out.to_csv(Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4") / "nhis_diagnosis.csv", index=False)
pd.set_option("display.width", 220)
print(out.drop(columns=["levers_present"]).round(3).to_string(index=False))
print(out[["dataset", "levers_present"]].to_string(index=False))
