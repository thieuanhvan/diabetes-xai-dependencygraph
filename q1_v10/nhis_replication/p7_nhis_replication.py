"""P7 replication on a third survey: CDC NHIS (Teboul-style schema).

Same protocol as the X1 pilot, single label (self-reported diagnosis), two generation modes:
  published   P4 per-query direction constraints (the audited system)
  no_ind      same, but indicators removed from features_to_vary (P7 Table V enforcement)
Audit = P7 depgraph edge rule (narrow reading). 5-fold cross-fitting, OOF p >= 0.5, top 200 by risk.

Run with the P7 repo venv:
    C:/Repos/uit/diabetes-xai-dependencygraph/.venv/Scripts/python.exe p7_nhis_replication.py --year 2022
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")
P7_REPO = Path("C:/Repos/uit/diabetes-xai-dependencygraph")
sys.path.insert(0, str(P7_REPO / "src"))
from depgraph.audit import classify, lever_in_neighbours  # noqa: E402
from depgraph.nodes import DIRECTION, TIER  # noqa: E402
import dice_ml  # noqa: E402

DATA_DIR = Path("C:/Repos/uit/nhis-diabetes/outputs/tabular")
OUT_DIR = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\nhis_replication") / "results"
TARGET = "Diabetes_binary"
SEEDS = [42, 123, 2024, 7, 31337]
XGB_PARAMS = dict(n_estimators=500, max_depth=6, learning_rate=0.05, subsample=0.9,
                  colsample_bytree=0.9, min_child_weight=1, reg_lambda=1.0,
                  tree_method="hist", eval_metric="auc", n_jobs=-1)
INDICATORS = {f for f, t in TIER.items() if t == "indicator"}


def load(year: int, csv: str = ""):
    path = Path(csv) if csv else DATA_DIR / f"cdc_nhis_diabetes_{year}.csv"
    d = pd.read_csv(path).dropna()
    feats = [c for c in d.columns if c not in (TARGET, "AgeGroup")]
    if "AgeGroup" in d.columns:  # NHIS: Age in years; BRFSS: Age is already the 1-13 group code
        d = d[d.Age >= 18]
    return d.reset_index(drop=True), feats


def holdout_fit(X, y, seed_split=42, seed_model=42):
    """P4/P7 protocol: one stratified 80/20 split, one classifier; only the generator seed varies."""
    from sklearn.model_selection import train_test_split
    idx = np.arange(len(X))
    tr, te = train_test_split(idx, test_size=0.2, stratify=y, random_state=seed_split)
    m = XGBClassifier(random_state=seed_model, **XGB_PARAMS).fit(X.iloc[tr], y.iloc[tr])
    p = np.full(len(X), -1.0); p[te] = m.predict_proba(X.iloc[te])[:, 1]
    fold_of = np.zeros(len(X), dtype=int)
    return p, fold_of, [m], [tr]


def oof_fit(X, y, seed):
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    p = np.zeros(len(X)); fold_of = np.zeros(len(X), dtype=int); models, tr_idx = [], []
    for k, (tr, te) in enumerate(skf.split(X, y)):
        m = XGBClassifier(random_state=seed, **XGB_PARAMS).fit(X.iloc[tr], y.iloc[tr])
        p[te] = m.predict_proba(X.iloc[te])[:, 1]; fold_of[te] = k
        models.append(m); tr_idx.append(tr)
    return p, fold_of, models, tr_idx


def constraints(x, lo, hi, feats, mode):
    vary, rng = [], {}
    for f in feats:
        dcls = DIRECTION.get(f, "immutable")
        if dcls in ("immutable", "conditional"):
            continue
        if mode == "no_ind" and f in INDICATORS:
            continue
        a, b = {"monotonic_up": (x[f], hi[f]), "monotonic_down": (lo[f], x[f])}.get(dcls, (lo[f], hi[f]))
        if float(b) - float(a) <= 1e-9:
            continue
        vary.append(f); rng[f] = [float(a), float(b)]
    return vary, rng


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2022)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seeds", default=",".join(map(str, SEEDS)))
    ap.add_argument("--modes", default="published,no_ind", help="published,no_ind,route_A")
    ap.add_argument("--max_rounds", type=int, default=8)
    ap.add_argument("--csv", default="", help="other Teboul-schema CSV (e.g. BRFSS 2021); --year is then only a label")
    ap.add_argument("--prefix", default="p7nhis")
    ap.add_argument("--dice_sample", type=int, default=0, help="rows given to dice_ml.Data (0 = all)")
    ap.add_argument("--holdout", action="store_true", help="P4/P7 protocol: fixed 80/20 split + fixed model")
    a = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    d, feats = load(a.year, a.csv)
    X = d[feats].astype(float); y = d[TARGET].astype(int)
    lo, hi = X.min(), X.max()
    print(f"{'csv' if a.csv else 'NHIS'} {a.year}: n={len(d)} prev={y.mean():.3f} features={feats}", flush=True)
    rows, meta = [], []
    for seed in [int(s) for s in a.seeds.split(",")]:
        t0 = time.time()
        p, fold_of, models, tr_idx = holdout_fit(X, y) if a.holdout else oof_fit(X, y, seed)
        pos = np.where(p >= 0.5)[0]
        order = pos[np.argsort(-p[pos])][: a.n]
        meta.append({"seed": seed, "auc": roc_auc_score(y[p >= 0], p[p >= 0]), "pos_pred": len(pos), "cohort": len(order)})
        print(meta[-1], flush=True)
        exps = {}
        for k, m in enumerate(models):
            tr = d.iloc[tr_idx[k]][feats + [TARGET]].astype(float)
            if a.dice_sample and len(tr) > a.dice_sample:
                # DiCE 'random' only uses the data for feature ranges; keep a stratified sample plus the
                # rows holding each feature's min and max so the ranges are exactly those of the full data
                ext = set(tr[feats].idxmin()) | set(tr[feats].idxmax())
                smp = tr.groupby(TARGET, group_keys=False).apply(
                    lambda g: g.sample(frac=a.dice_sample / len(tr), random_state=seed))
                tr = pd.concat([smp, tr.loc[sorted(ext - set(smp.index))]])
            exps[k] = (dice_ml.Dice(dice_ml.Data(dataframe=tr, continuous_features=feats, outcome_name=TARGET),
                                    dice_ml.Model(model=m, backend="sklearn"), method="random"), m)
        for mode in a.modes.split(","):
            for qi, i in enumerate(order):
                exp, m = exps[fold_of[i]]
                vary, rng = constraints(X.iloc[i], lo, hi, feats, "no_ind" if mode == "no_ind" else "published")
                base = {"year": a.year, "mode": mode, "seed": seed, "pid": int(i)}
                orig = X.iloc[i].round(0)
                kept, rounds = [], 0
                for r in range(a.max_rounds if mode == "route_A" else 1):
                    rounds = r + 1
                    try:
                        cfs = exp.generate_counterfactuals(X.iloc[[i]], total_CFs=5, desired_class=0,
                                                           features_to_vary=vary, permitted_range=rng,
                                                           random_seed=seed + qi + 1000 * r, verbose=False
                                                           ).cf_examples_list[0].final_cfs_df
                    except Exception:
                        cfs = None
                    if cfs is None or len(cfs) == 0:
                        continue
                    cfs = cfs[feats].astype(float).round(0)
                    pr = m.predict_proba(cfs)[:, 1]
                    for j in range(len(cfs)):
                        ch = [f for f in feats if abs(cfs.iloc[j][f] - orig[f]) > 1e-9]
                        if mode == "route_A":
                            S = set(ch)
                            # universal reading: every moved indicator needs a pulled lever with an edge into it
                            if any(not (lever_in_neighbours(v) & S) for v in S & INDICATORS):
                                continue
                            key = tuple(cfs.iloc[j].tolist())
                            if key in {k for k, _, _ in kept}:
                                continue
                        else:
                            key = None
                        kept.append((key, ch, bool(pr[j] < 0.5)))
                        if len(kept) >= 5:
                            break
                    if len(kept) >= 5:
                        break
                if not kept:
                    rows.append({**base, "cf_id": -1, "changed": "", "valid": np.nan, "rounds": rounds}); continue
                for j, (_, ch, v) in enumerate(kept[:5]):
                    rows.append({**base, "cf_id": j, "changed": ";".join(ch), "valid": v, "rounds": rounds})
        print(f"  seed {seed} done in {time.time() - t0:.0f}s", flush=True)
        pd.DataFrame(rows).to_csv(OUT_DIR / f"{a.prefix}_cf_changes_{a.year}_{a.modes.replace(',','-')}.csv", index=False)
    df = pd.DataFrame(rows)
    pd.DataFrame(meta).to_csv(OUT_DIR / f"{a.prefix}_meta_{a.year}_{a.modes.replace(',','-')}.csv", index=False)
    out = []
    for (mode, seed), g in df.groupby(["mode", "seed"]):
        n_fail = g[g.cf_id < 0].pid.nunique()
        g = g[g.cf_id >= 0]
        sets = [set(s.split(";")) - {""} for s in g.changed.fillna("")]
        cl = [classify(s, reading="narrow", rule="edge") for s in sets]
        allch = [f for s in sets for f in s]
        out.append({"year": a.year, "mode": mode, "seed": seed, "n_cf": len(g), "queries_no_cf": n_fail,
                    "validity": g.valid.mean(),
                    "indicator_change_share": sum(f in INDICATORS for f in allch) / max(len(allch), 1),
                    "cf_touch_indicator": np.mean([r["touches_target"] for r in cl]),
                    "cf_unsupported": np.mean([r["unsupported"] for r in cl]),
                    "cf_fully_unactionable": np.mean([r["fully_unactionable"] for r in cl]),
                    "share_GenHlth": sum(f == "GenHlth" for f in allch) / max(len(allch), 1),
                    "share_DiffWalk": sum(f == "DiffWalk" for f in allch) / max(len(allch), 1),
                    "share_MentHlth": sum(f == "MentHlth" for f in allch) / max(len(allch), 1),
                    "mean_rounds": g.groupby("pid").rounds.first().mean() if "rounds" in g else np.nan})
    s = pd.DataFrame(out)
    s.to_csv(OUT_DIR / f"{a.prefix}_summary_{a.year}_{a.modes.replace(',','-')}.csv", index=False)
    print(s.groupby("mode").mean(numeric_only=True).T.round(4).to_string())
    pv = s.pivot(index="seed", columns="mode", values="validity")
    for mo in pv.columns:
        if mo != "published" and "published" in pv:
            print(f"validity {mo} - published per seed:", (pv[mo] - pv["published"]).round(4).tolist())


if __name__ == "__main__":
    main()
