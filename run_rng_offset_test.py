"""Why does the published run report 1,520 feature changes and the audit
dump 1,500, with the same model, the same cohort and the same dice-ml?

Hypothesis. The published run executes compare_modes=True: global mode
first, per-query mode second, in ONE process (src/pipelines/main.py, the
`else:` branch at line ~279). run_audit_dump.py runs per-query ONLY. DiCE's
`random` method draws from the process-global NumPy RNG, so the 200x5 draws
consumed by the global pass leave per-query starting from a different RNG
state. Same distribution, different sample.

Test. Load the SAVED model artefact so the classifier and the cohort are
bit-identical to the platform of record, then generate per-query
counterfactuals twice:

  ARM 1  seed -> per-query                    (what run_audit_dump.py does)
  ARM 2  seed -> global -> per-query          (what the published run does)

If the hypothesis holds, ARM 1 reproduces ~1500 and ARM 2 lands near 1520,
and ARM 1 != ARM 2 feature by feature in BOTH directions.

Run from the dependency-graph repo root with the pipeline repo as a sibling.
"""
from __future__ import annotations

import collections
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO = Path(os.environ.get(
    "PIPELINE_REPO",
    Path(__file__).parent.parent / "diabetes-xai-counterfactual",
)).resolve()
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.pipelines.counterfactual.dice_runner import DiCEConfig, DiCERunner
from src.pipelines.counterfactual.feature_taxonomy import get_discrete_features
from src.pipelines.data.loader import TARGET_COL, load_dataset
from src.pipelines.preprocessing.pipeline import get_train_test_split
from src.utils.seed import seed_everything

cfg = yaml.safe_load(open(REPO / "configs" / "default.yaml"))
SEED = cfg["random"]["seed"]

print("[setup] loading BRFSS 2021 ...")
X, y = load_dataset(REPO / cfg["paths"]["data_csv"])
X_train, X_test, y_train, y_test = get_train_test_split(
    X, y,
    test_size=cfg["split"]["test_size"],
    seed=SEED,
    stratify=cfg["split"]["stratify"],
)

import joblib
model = joblib.load(REPO / "demo" / "models" / "xgb_brfss2021.joblib")
proba = model.predict_proba(X_test.values)[:, 1]
n_eval = min(cfg["evaluate"]["n_test_instances"], len(X_test))
high_risk_idx = np.argsort(proba)[-n_eval:]
queries = X_test.iloc[high_risk_idx].reset_index(drop=True)
print(f"[setup] artefact loaded. max proba {proba.max():.6f}  "
      f"top-200 mean {proba[high_risk_idx].mean():.6f}  "
      f"cutoff {proba[high_risk_idx].min():.6f}")
print("[setup] published cohort constants: max 0.887033  mean 0.747455  "
      "cutoff 0.694780")

discrete = set(get_discrete_features())


def runner(per_query: bool) -> DiCERunner:
    return DiCERunner(
        model=model, X_train=X_train, y_train=y_train, target_col=TARGET_COL,
        config=DiCEConfig(
            method=cfg["dice"]["method"],
            n_counterfactuals=cfg["dice"]["n_counterfactuals"],
            desired_class=cfg["dice"]["desired_class"],
            proximity_weight=cfg["dice"]["proximity_weight"],
            diversity_weight=cfg["dice"]["diversity_weight"],
            per_query=per_query,
        ),
    )


def count_changes(cf_examples):
    """Exactly the counting rule of run_audit_dump.py."""
    per_feature = collections.Counter()
    n_cf = 0
    for i in range(len(queries)):
        q = queries.iloc[i]
        obj = cf_examples[i]
        cfs = obj.final_cfs_df if obj is not None else None
        if cfs is None or len(cfs) == 0:
            continue
        cfs_df = cfs.drop(columns=[TARGET_COL]) if TARGET_COL in cfs.columns else cfs
        cfs_df = cfs_df.copy()
        for c in discrete:
            if c in cfs_df.columns:
                cfs_df[c] = cfs_df[c].round().astype(int)
        for k in range(len(cfs_df)):
            n_cf += 1
            cf = cfs_df.iloc[k]
            for f in queries.columns:
                before, after = float(q[f]), float(cf[f])
                if f in discrete:
                    if int(round(before)) != int(round(after)):
                        per_feature[f] += 1
                else:
                    if abs(before - after) > 1e-6:
                        per_feature[f] += 1
    return per_feature, n_cf


print("\n[ARM 1] seed -> per-query only   (run_audit_dump.py)")
seed_everything(SEED)
pf1, ncf1 = count_changes(runner(True).generate(queries))
print(f"        counterfactuals {ncf1}   TOTAL CHANGES {sum(pf1.values())}")

print("\n[ARM 2] seed -> global -> per-query   (published compare_modes run)")
seed_everything(SEED)
r = runner(False)
_ = r.generate(queries)           # global pass, output discarded
pf2, ncf2 = count_changes(runner(True).generate(queries))
print(f"        counterfactuals {ncf2}   TOTAL CHANGES {sum(pf2.values())}")

P4 = {"BMI": 705, "Education": 42, "Fruits": 13, "GenHlth": 218,
      "HighBP": 139, "HighChol": 107, "Income": 128, "MentHlth": 43,
      "NoDocbcCost": 5, "PhysActivity": 30, "PhysHlth": 78, "Smoker": 5,
      "Veggies": 7}

print(f"\n{'feature':16s}{'P4=1520':>9s}{'ARM1':>8s}{'ARM2':>8s}"
      f"{'A1-P4':>8s}{'A2-P4':>8s}")
for f in sorted(set(P4) | set(pf1) | set(pf2)):
    a, b, c = P4.get(f, 0), pf1.get(f, 0), pf2.get(f, 0)
    print(f"{f:16s}{a:9d}{b:8d}{c:8d}{b-a:8d}{c-a:8d}")
t0, t1, t2 = sum(P4.values()), sum(pf1.values()), sum(pf2.values())
print(f"{'TOTAL':16s}{t0:9d}{t1:8d}{t2:8d}{t1-t0:8d}{t2-t0:8d}")
print(f"\nL1 distance from the published per-feature vector: "
      f"ARM1 {sum(abs(pf1.get(f,0)-P4.get(f,0)) for f in set(P4)|set(pf1))}   "
      f"ARM2 {sum(abs(pf2.get(f,0)-P4.get(f,0)) for f in set(P4)|set(pf2))}")
