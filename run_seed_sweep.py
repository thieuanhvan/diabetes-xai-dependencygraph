"""Multi-seed sweep (paper Section VI robustness check).

Runs BOTH configurations across the five seeds used by the audited paper's own
multi-seed ablation: {42, 123, 2024, 7, 31337}. The seed varies XGBoost
training, the train/test split, and DiCE sampling.

  Config A  published per-query taxonomy
  Config B  A + indicators (GenHlth, PhysHlth, MentHlth) reclassified as
            non-levers, hence excluded from features_to_vary

Question: is the validity gain of Config B real, or seed noise?
The audited paper reports CV = 0.72% on validity across these five seeds.
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
from src.pipelines.evaluate.cf_metrics import validity
from src.pipelines.models.xgb_train import XGBConfig, train_xgb
from src.pipelines.preprocessing.pipeline import get_train_test_split
from src.utils.seed import seed_everything

SEEDS = [42, 123, 2024, 7, 31337]
INDICATORS = ["GenHlth", "PhysHlth", "MentHlth"]
LEVER = {"BMI", "PhysActivity", "Fruits", "Veggies", "Smoker", "HvyAlcoholConsump", "NoDocbcCost"}

cfg = yaml.safe_load(open(REPO / "configs" / "default.yaml"))
X, y = load_dataset(REPO / cfg["paths"]["data_csv"])
discrete = set(get_discrete_features())

# Snapshot the pristine taxonomy so Config A is never contaminated by Config B.
PRISTINE = dict(FT.FEATURE_TAXONOMY)


def one(seed: int, graph: bool) -> dict:
    FT.FEATURE_TAXONOMY.clear()
    FT.FEATURE_TAXONOMY.update(PRISTINE)
    if graph:
        for f in INDICATORS:
            s = PRISTINE[f]
            FT.FEATURE_TAXONOMY[f] = FT.FeatureSpec(
                s.name, FT.Mutability.CONDITIONAL, s.value_range, s.semantic_label
            )

    seed_everything(seed)
    Xtr, Xte, ytr, yte = get_train_test_split(
        X, y, test_size=cfg["split"]["test_size"], seed=seed, stratify=cfg["split"]["stratify"]
    )
    xgb_cfg = dict(cfg["xgboost"]); xgb_cfg["random_state"] = seed
    res = train_xgb(Xtr, ytr, Xte, yte, XGBConfig(**xgb_cfg))
    n_eval = min(cfg["evaluate"]["n_test_instances"], len(Xte))
    queries = Xte.iloc[np.argsort(res["proba"])[-n_eval:]].reset_index(drop=True)

    seed_everything(seed)
    runner = DiCERunner(
        model=res["model"], X_train=Xtr, y_train=ytr, target_col=TARGET_COL,
        config=DiCEConfig(
            method=cfg["dice"]["method"], n_counterfactuals=cfg["dice"]["n_counterfactuals"],
            desired_class=cfg["dice"]["desired_class"],
            proximity_weight=cfg["dice"]["proximity_weight"],
            diversity_weight=cfg["dice"]["diversity_weight"], per_query=True,
        ),
    )
    cfe = runner.generate(queries)

    vals, acts = [], []
    n_chg = n_ind = n_unsup = n_pure = n_cf = n_nocf = 0
    for i in range(len(queries)):
        q = queries.iloc[i]; obj = cfe[i]
        cfs = obj.final_cfs_df if obj is not None else None
        if cfs is None or len(cfs) == 0:
            n_nocf += 1
            continue
        d = cfs.drop(columns=[TARGET_COL]) if TARGET_COL in cfs.columns else cfs
        d = d.copy()
        for c in discrete:
            if c in d.columns:
                d[c] = d[c].round().astype(int)
        preds = res["model"].predict(d.values)
        vals.append(validity(preds, cfg["dice"]["desired_class"]))
        acts.append(float(np.mean([actionability_score(q, d.iloc[j])["score"] for j in range(len(d))])))
        for k in range(len(d)):
            n_cf += 1
            chg = []
            for f in queries.columns:
                b, a = float(q[f]), float(d[f].iloc[k])
                if (int(round(b)) != int(round(a))) if f in discrete else abs(b - a) > 1e-6:
                    chg.append(f)
            n_chg += len(chg)
            ind = [f for f in chg if f in INDICATORS]
            lev = [f for f in chg if f in LEVER]
            trt = [f for f in chg if f in {"HighBP", "HighChol"}]
            n_ind += len(ind)
            if ind and not lev:
                n_unsup += 1
                if not trt:
                    n_pure += 1
    return {
        "seed": seed, "config": "graph" if graph else "published",
        "auc": round(float(res["auc"]), 4),
        "validity": round(float(np.mean(vals)), 4),
        "actionability": round(float(np.mean(acts)), 4),
        "total_changes": n_chg, "indicator_changes": n_ind,
        "unsupported_cfs": n_unsup, "pure_indicator_cfs": n_pure,
        "queries_no_cf": n_nocf,
    }


rows = []
for s in SEEDS:
    for graph in (False, True):
        r = one(s, graph)
        rows.append(r)
        print(f"seed={s:6d} {r['config']:10s} AUC={r['auc']:.4f} "
              f"validity={r['validity']:.4f} ind={r['indicator_changes']:4d} "
              f"unsup={r['unsupported_cfs']:4d}", flush=True)
        pd.DataFrame(rows).to_csv(REPO / "outputs_kg" / "seed_sweep.csv", index=False)

df = pd.DataFrame(rows)
print("\n" + "=" * 70)
piv = df.pivot(index="seed", columns="config", values="validity")
piv["delta"] = piv["graph"] - piv["published"]
print(piv.to_string())
print("=" * 70)
pub, gr = df[df.config == "published"]["validity"], df[df.config == "graph"]["validity"]
d = piv["delta"]
print(f"\npublished validity : mean={pub.mean():.4f}  sd={pub.std():.4f}  CV={pub.std()/pub.mean()*100:.2f}%")
print(f"graph     validity : mean={gr.mean():.4f}  sd={gr.std():.4f}  CV={gr.std()/gr.mean()*100:.2f}%")
print(f"\nΔ validity         : mean={d.mean():+.4f}  sd={d.std():.4f}  "
      f"min={d.min():+.4f}  max={d.max():+.4f}")
print(f"Δ positive in {(d > 0).sum()}/{len(d)} seeds")
from scipy import stats
t, p = stats.ttest_rel(gr.values, pub.values)
print(f"paired t-test      : t={t:.3f}  p={p:.4f}")
