"""Is the released classifier reproducible by retraining?

run_check_model_repro.py  -  v2, 2026-07-26.
If your copy is about twenty lines long, it is the inline snippet from the chat
and not this file. Replace it.

WHY THIS FILE EXISTS
--------------------
Every number in the audit descends from one object: the set of two hundred
highest-risk patients in the test split. That set is an argsort of the
classifier's predicted probabilities, so any shift in those probabilities can
reorder it, and a reordered cohort means different queries, different
counterfactuals, and different figures throughout.

On 2026-07-26 a retrain on Linux, with the seed, the split and the pinned
library versions of requirements.txt, produced probabilities differing from the
released artefact by up to 0.019, and the audit then reported 1,523 recommended
changes where the released dump has 1,500. The same retrain on Windows appears
to reproduce the artefact, since outputs/seed_sweep.csv was produced by
retraining and agrees with the artefact at seed 42.

If that is right, the finding is narrower than "retraining does not reproduce"
and should be written as cross-platform sensitivity instead. This script settles
it in about thirty seconds and prints which of the two the manuscript should
say.

WHAT IT CHECKS
--------------
  1. artefact against its own stored predictions   (sanity; must be ~1e-8)
  2. a fresh retrain against the artefact          (the question)
  3. whether the two agree on the top-200 COHORT MEMBERSHIP, not merely on
     summary statistics, because membership is what propagates

USAGE
-----
Right-click run. Place at the root of diabetes-xai-dependencygraph, beside
run_route_enforce.py. Trains once, generates nothing.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def _find_pipeline_repo() -> Path:
    tried = []
    env = os.environ.get("PIPELINE_REPO")
    for cand in (Path(env) if env else None,
                 Path(__file__).resolve().parent.parent / "diabetes-xai-counterfactual",
                 Path(r"C:\Projects\uit\diabetes-xai-counterfactual")):
        if cand is None:
            continue
        tried.append(str(cand))
        if cand.exists():
            return cand.resolve()
    raise SystemExit("Cannot locate diabetes-xai-counterfactual. Tried:\n  "
                     + "\n  ".join(tried))


REPO = _find_pipeline_repo()
print(f"[paths] pipeline repo: {REPO}")
sys.path.insert(0, str(REPO))

from src.pipelines.data.loader import load_dataset
from src.pipelines.models.xgb_train import XGBConfig, train_xgb
from src.pipelines.preprocessing.pipeline import get_train_test_split
from src.utils.seed import seed_everything

import joblib
import platform
import sklearn
import xgboost

N_COHORT = 200
MODEL_PATH = REPO / "demo" / "models" / "xgb_brfss2021.joblib"
PROBA_PATH = REPO / "demo" / "models" / "proba_test.parquet"

print(f"[env] {platform.platform()}")
print(f"[env] python {platform.python_version()}  numpy {np.__version__}  "
      f"pandas {pd.__version__}  sklearn {sklearn.__version__}  "
      f"xgboost {xgboost.__version__}")

cfg = yaml.safe_load(open(REPO / "configs" / "default.yaml"))
seed_everything(cfg["random"]["seed"])
X, y = load_dataset(REPO / cfg["paths"]["data_csv"])
X_train, X_test, y_train, y_test = get_train_test_split(
    X, y, test_size=cfg["split"]["test_size"],
    seed=cfg["random"]["seed"], stratify=cfg["split"]["stratify"],
)
print(f"[data] {X.shape[0]} rows, {X.shape[1]} features; "
      f"test {len(X_test)}, prevalence {float(y_test.mean()):.4f}")


def summarise(p: np.ndarray, label: str) -> dict:
    top = np.sort(p)[-N_COHORT:]
    d = {"label": label, "max": float(p.max()), "cohort_mean": float(top.mean()),
         "cohort_cutoff": float(top.min())}
    print(f"[{label:22s}] max {d['max']:.6f}  cohort mean {d['cohort_mean']:.6f}"
          f"  cutoff {d['cohort_cutoff']:.6f}")
    return d


# ---------------------------------------------------------------------------
# 1. the artefact, and the predictions stored beside it
# ---------------------------------------------------------------------------
model_art = joblib.load(MODEL_PATH)
p_art = model_art.predict_proba(X_test.values)[:, 1]
s_art = summarise(p_art, "artefact")

# Optional. Reading it needs a parquet engine (pyarrow or fastparquet), which
# the pinned requirements do not include; the sibling repo installs pyarrow only
# for its Streamlit demo. This check is a sanity check on the artefact and plays
# no part in the verdict, so a missing engine must not stop the run.
stored = None
if PROBA_PATH.exists():
    try:
        stored = pd.read_parquet(PROBA_PATH).select_dtypes("number").iloc[:, 0].values
    except Exception as exc:                      # noqa: BLE001
        print(f"[check 1] skipped, cannot read {PROBA_PATH.name}: "
              f"{type(exc).__name__}. Install pyarrow if you want this check; "
              f"it is not needed for the verdict.")
    if stored is not None:
        if len(stored) == len(p_art):
            d = float(np.abs(np.sort(stored) - np.sort(p_art)).max())
            print(f"[check 1] artefact against its stored predictions: "
                  f"max |delta| {d:.3e}   -> "
                  f"{'consistent' if d < 1e-6 else 'INCONSISTENT'}")
        else:
            print(f"[check 1] length mismatch, stored {len(stored)} "
                  f"vs {len(p_art)}; skipped")
else:
    print(f"[check 1] skipped, {PROBA_PATH.name} not found")

# ---------------------------------------------------------------------------
# 2. a fresh retrain
# ---------------------------------------------------------------------------
print("[train] retraining from configs/default.yaml ...")
seed_everything(cfg["random"]["seed"])
res = train_xgb(X_train, y_train, X_test, y_test, XGBConfig(**cfg["xgboost"]))
p_new = res["proba"]
s_new = summarise(p_new, "retrained")
print(f"[auc] retrained {res['auc']:.6f}   published 0.8233")

d_mean = float(np.abs(p_new - p_art).mean())
d_max = float(np.abs(p_new - p_art).max())
print(f"[check 2] retrain against artefact: mean |delta| {d_mean:.6e}  "
      f"max |delta| {d_max:.6e}")

# ---------------------------------------------------------------------------
# 3. cohort membership, which is what propagates
# ---------------------------------------------------------------------------
idx_art = set(np.argsort(p_art)[-N_COHORT:].tolist())
idx_new = set(np.argsort(p_new)[-N_COHORT:].tolist())
shared = len(idx_art & idx_new)
print(f"[check 3] top-{N_COHORT} cohort membership: {shared}/{N_COHORT} shared, "
      f"{N_COHORT - shared} differ")

order_same = bool(np.array_equal(np.argsort(p_art)[-N_COHORT:],
                                np.argsort(p_new)[-N_COHORT:]))
print(f"[check 3] cohort ORDER identical: {order_same}")

# ---------------------------------------------------------------------------
# verdict, phrased as the sentence the manuscript should carry
# ---------------------------------------------------------------------------
BITWISE = d_max < 1e-9
IDENTICAL_COHORT = (shared == N_COHORT) and order_same

print("\n" + "=" * 78)
if BITWISE:
    print("VERDICT: retraining reproduces the artefact bit for bit on this machine.")
    print("The manuscript should NOT claim that retraining fails to reproduce.")
    print("Write it as CROSS-PLATFORM sensitivity: the artefact and a retrain on")
    print("the original platform agree exactly, while a retrain on a different")
    print("platform diverged by up to 0.019 and reordered the cohort. Report the")
    print("platform of record, and say that the artefact is what makes the")
    print("results reproducible off it.")
elif IDENTICAL_COHORT:
    print("VERDICT: probabilities differ but the top-200 cohort is IDENTICAL in")
    print("membership and order. Downstream figures are therefore unaffected, and")
    print("the reproducibility note should be scoped to the probabilities alone,")
    print("not to the audit results. Loading the artefact remains the safer")
    print("default but is not load-bearing.")
else:
    print("VERDICT: retraining does NOT reproduce the artefact on this machine,")
    print(f"and the cohort differs in {N_COHORT - shared} of {N_COHORT} members.")
    print("The reproducibility paragraph stands as written: pinning library")
    print("versions is not sufficient, and the fitted model must be released for")
    print("results of this kind to be reproducible. Keep USE_SAVED_MODEL = True.")
print("=" * 78)

out = REPO / "outputs_kg"
out.mkdir(exist_ok=True)
pd.DataFrame([
    {**s_art, "auc": np.nan},
    {**s_new, "auc": float(res["auc"])},
]).assign(
    delta_mean_vs_artefact=[0.0, d_mean],
    delta_max_vs_artefact=[0.0, d_max],
    cohort_shared=[N_COHORT, shared],
    cohort_order_identical=[True, order_same],
    platform=platform.platform(),
    python=platform.python_version(),
    xgboost=xgboost.__version__,
).to_csv(out / "model_reproducibility.csv", index=False)
print(f"-> {out / 'model_reproducibility.csv'}")