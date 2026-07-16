"""Enforcement run (paper Section VI).

Identical to the published per-query configuration in every respect except one:
the three self-reported health-status indicators (GenHlth, PhysHlth, MentHlth)
are reclassified CONDITIONAL, which the existing taxonomy already excludes from
features_to_vary. Nothing else changes: same seed, same split, same classifier,
same DiCE backend, same cohort.

Question: what does it cost to stop recommending things the patient cannot do?
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

from src.pipelines.counterfactual import feature_taxonomy as FT
from src.pipelines.counterfactual.actionability import actionability_score
from src.pipelines.counterfactual.dice_runner import DiCEConfig, DiCERunner
from src.pipelines.counterfactual.feature_taxonomy import get_discrete_features
from src.pipelines.data.loader import TARGET_COL, load_dataset
from src.pipelines.evaluate.cf_metrics import proximity_l1, sparsity, validity
from src.pipelines.models.xgb_train import XGBConfig, train_xgb
from src.pipelines.preprocessing.pipeline import get_train_test_split
from src.utils.seed import seed_everything

INDICATORS = ["GenHlth", "PhysHlth", "MentHlth"]

cfg = yaml.safe_load(open(REPO / "configs" / "default.yaml"))
seed_everything(cfg["random"]["seed"])

X, y = load_dataset(REPO / cfg["paths"]["data_csv"])
X_train, X_test, y_train, y_test = get_train_test_split(
    X, y, test_size=cfg["split"]["test_size"],
    seed=cfg["random"]["seed"], stratify=cfg["split"]["stratify"],
)
res = train_xgb(X_train, y_train, X_test, y_test, XGBConfig(**cfg["xgboost"]))
n_eval = min(cfg["evaluate"]["n_test_instances"], len(X_test))
high_risk_idx = np.argsort(res["proba"])[-n_eval:]
queries = X_test.iloc[high_risk_idx].reset_index(drop=True)

discrete = set(get_discrete_features())
ranges = FT.get_feature_ranges()


def run(label: str) -> dict:
    seed_everything(cfg["random"]["seed"])
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
    cfe = runner.generate(queries)

    val, act, prox, spar = [], [], [], []
    ind_changes = n_changes = n_no_cf = 0
    for i in range(len(queries)):
        q = queries.iloc[i]
        obj = cfe[i]
        cfs = obj.final_cfs_df if obj is not None else None
        if cfs is None or len(cfs) == 0:
            n_no_cf += 1
            continue
        d = cfs.drop(columns=[TARGET_COL]) if TARGET_COL in cfs.columns else cfs
        d = d.copy()
        for c in discrete:
            if c in d.columns:
                d[c] = d[c].round().astype(int)
        preds = res["model"].predict(d.values)
        val.append(validity(preds, cfg["dice"]["desired_class"]))
        prox.append(proximity_l1(q, d, ranges))
        spar.append(sparsity(q, d))
        act.append(float(np.mean([actionability_score(q, d.iloc[j])["score"] for j in range(len(d))])))
        for k in range(len(d)):
            for f in queries.columns:
                b, a = float(q[f]), float(d[f].iloc[k])
                ch = (int(round(b)) != int(round(a))) if f in discrete else abs(b - a) > 1e-6
                if ch:
                    n_changes += 1
                    if f in INDICATORS:
                        ind_changes += 1
    return {
        "label": label,
        "validity": float(np.mean(val)),
        "actionability": float(np.mean(act)),
        "proximity_L1": float(np.mean(prox)),
        "sparsity": float(np.mean(spar)),
        "n_changes": n_changes,
        "indicator_changes": ind_changes,
        "queries_with_no_cf": n_no_cf,
    }


print("[A] published per-query configuration ...")
base = run("per-query (published)")

print("[B] graph-constrained: indicators removed from features_to_vary ...")
for f in INDICATORS:
    s = FT.FEATURE_TAXONOMY[f]
    FT.FEATURE_TAXONOMY[f] = FT.FeatureSpec(s.name, FT.Mutability.CONDITIONAL, s.value_range, s.semantic_label)
graph = run("per-query + graph (levers/treatables only)")

df = pd.DataFrame([base, graph])
out = REPO / "outputs_kg"
out.mkdir(exist_ok=True)
df.to_csv(out / "enforcement_comparison.csv", index=False)

print("\n" + "=" * 78)
print(df.to_string(index=False))
print("=" * 78)
dv = graph["validity"] - base["validity"]
print(f"\nΔ validity      : {dv:+.4f}   ({dv/base['validity']*100:+.1f}% relative)")
print(f"Δ sparsity      : {graph['sparsity'] - base['sparsity']:+.4f}")
print(f"indicator changes: {base['indicator_changes']} -> {graph['indicator_changes']}")
print(f"total changes    : {base['n_changes']} -> {graph['n_changes']}")
