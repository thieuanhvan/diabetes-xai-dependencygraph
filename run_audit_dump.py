"""Reproduce the published per-query CF run and dump RAW per-CF feature changes.

Reuses the repository's own modules verbatim (loader, split, XGBoost, DiCE
runner, taxonomy) so the run reproduces the state tagged v1.0-ijmi. The only
addition is that every individual counterfactual's feature-level changes are
written out, which the published pipeline aggregates away.

Output: outputs_kg/raw_cf_changes.csv   (one row per changed feature per CF)
        outputs_kg/raw_cf_index.csv     (one row per CF: validity, n_changes)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

import os
# Locate the published pipeline (diabetes-xai-counterfactual @ tag v1.0-ijmi).
# Set PIPELINE_REPO, or place that repo as a sibling of this one.
REPO = Path(os.environ.get(
    "PIPELINE_REPO",
    Path(__file__).parent.parent / "diabetes-xai-counterfactual",
)).resolve()
sys.path.insert(0, str(REPO))
P7SRC = Path(__file__).parent / "src"   # this repo's own module
sys.path.insert(0, str(P7SRC))

from src.pipelines.counterfactual.dice_runner import DiCEConfig, DiCERunner
from src.pipelines.counterfactual.feature_taxonomy import get_discrete_features
from src.pipelines.data.loader import TARGET_COL, load_dataset
from src.pipelines.models.xgb_train import XGBConfig, train_xgb
from src.pipelines.preprocessing.pipeline import get_train_test_split
from src.utils.seed import seed_everything

cfg = yaml.safe_load(open(REPO / "configs" / "default.yaml"))
seed_everything(cfg["random"]["seed"])

print("[1/4] loading BRFSS 2021 ...")
X, y = load_dataset(REPO / cfg["paths"]["data_csv"])
print(f"      X={X.shape}  prevalence={y.mean():.4f}")

print("[2/4] split + train XGBoost ...")
X_train, X_test, y_train, y_test = get_train_test_split(
    X, y,
    test_size=cfg["split"]["test_size"],
    seed=cfg["random"]["seed"],
    stratify=cfg["split"]["stratify"],
)
res = train_xgb(X_train, y_train, X_test, y_test, XGBConfig(**cfg["xgboost"]))
print(f"      test AUC = {res['auc']:.4f}   (published: 0.8233)")

n_eval = min(cfg["evaluate"]["n_test_instances"], len(X_test))
high_risk_idx = np.argsort(res["proba"])[-n_eval:]
queries = X_test.iloc[high_risk_idx].reset_index(drop=True)
q_proba = res["proba"][high_risk_idx]
print(f"      top-{n_eval} cohort: base P mean={q_proba.mean():.4f} "
      f"min={q_proba.min():.4f} max={q_proba.max():.4f}   (published mean 0.7475)")

print("[3/4] generating per-query CFs (DiCE) ...")
runner = DiCERunner(
    model=res["model"], X_train=X_train, y_train=y_train, target_col=TARGET_COL,
    config=DiCEConfig(
        method=cfg["dice"]["method"],
        n_counterfactuals=cfg["dice"]["n_counterfactuals"],
        desired_class=cfg["dice"]["desired_class"],
        proximity_weight=cfg["dice"]["proximity_weight"],
        diversity_weight=cfg["dice"]["diversity_weight"],
        per_query=True,
    ),
)
cf_examples = runner.generate(queries)

print("[4/4] dumping raw per-CF changes ...")
discrete = set(get_discrete_features())
chg_rows, idx_rows = [], []
n_skipped = 0

for i in range(len(queries)):
    q = queries.iloc[i]
    obj = cf_examples[i]
    cfs = obj.final_cfs_df if obj is not None else None
    if cfs is None or len(cfs) == 0:
        n_skipped += 1
        continue
    cfs_df = cfs.drop(columns=[TARGET_COL]) if TARGET_COL in cfs.columns else cfs
    cfs_df = cfs_df.copy()
    for c in discrete:
        if c in cfs_df.columns:
            cfs_df[c] = cfs_df[c].round().astype(int)
    preds = res["model"].predict(cfs_df.values)

    for k in range(len(cfs_df)):
        cf = cfs_df.iloc[k]
        changed = []
        for f in queries.columns:
            before, after = float(q[f]), float(cf[f])
            if f in discrete:
                if int(round(before)) != int(round(after)):
                    changed.append((f, before, after))
            else:  # BMI
                if abs(before - after) > 1e-6:
                    changed.append((f, before, after))
        for f, b, a in changed:
            chg_rows.append({
                "query_i": i, "cf_k": k, "feature": f,
                "x_before": b, "x_after": a, "delta": a - b,
            })
        idx_rows.append({
            "query_i": i, "cf_k": k,
            "base_proba": float(q_proba[i]),
            "cf_pred": int(preds[k]),
            "valid": int(preds[k] == cfg["dice"]["desired_class"]),
            "n_changes": len(changed),
        })

out = REPO / "outputs_kg"
out.mkdir(exist_ok=True)
pd.DataFrame(chg_rows).to_csv(out / "raw_cf_changes.csv", index=False)
pd.DataFrame(idx_rows).to_csv(out / "raw_cf_index.csv", index=False)

n_changes = len(chg_rows)
print(f"\n      queries with no CF: {n_skipped}")
print(f"      CFs dumped        : {len(idx_rows)}")
print(f"      TOTAL CF CHANGES  : {n_changes}   (published Table 8 per-query total: 1520)")
print(f"      -> {out/'raw_cf_changes.csv'}")
