"""POST HOC (S-P1, S-P2), exploratory: thin wrapper around the FROZEN A2 scripts a2_ckd_runs.py and
a2_ckd_analysis.py (prereg v3 SHA-256 95a83da5..., unchanged). Plan: prereg/posthoc_ses_freeze_plan_en_v1_20261112_0726.md.

What the wrapper changes, in memory only (nothing in the frozen scripts or their outputs is touched):
  --ses-freeze      Education, Income and AnyHealthcare are made IMMUTABLE in the P4 taxonomy in every mode
                    (published, lock, route-aware, capped) on top of the frozen A2 patches (S-P1).
  --split-seed s    the train/test split seed and the XGBoost random_state are set to s instead of 42 (S-P2);
                    every XGBoost hyperparameter stays as configs/default.yaml.
  --tag name        outputs go to outputs/q1_posthoc_ses_splits/<name>/ (a2_model, a2_runs_main, a2_analysis).
Seed 42 runs (the SES-freeze run) must reproduce the frozen A2 test probabilities exactly before any
counterfactual is generated; otherwise the run stops.

Usage (P4 venv, isolated, below normal):
  python -I ps_ckd_runs.py --tag ses_freeze --ses-freeze
  python -I ps_ckd_runs.py --tag split_11 --split-seed 11
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
for p in (str(TOOLS / "q1_domain_ckd"), str(TOOLS / "crossdataset_p4")):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

OUTROOT = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/q1_posthoc_ses_splits")
FROZEN_PROBA = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/q1_domain_ckd/a2_model/test_proba.csv")
SES = ["Education", "Income", "AnyHealthcare"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--ses-freeze", action="store_true")
    ap.add_argument("--split-seed", type=int, default=42)
    ap.add_argument("--skip-runs", action="store_true")
    a = ap.parse_args()

    import a2_domain as D
    import a2_ckd_runs as R
    import p7_cross_p4pipeline as P

    out = OUTROOT / a.tag
    out.mkdir(parents=True, exist_ok=True)
    D.OUT = out
    R.MODEL_DIR = out / "a2_model"
    s = a.split_seed
    P.CFG["random"]["seed"] = s
    P.CFG["xgboost"]["random_state"] = s

    if a.ses_freeze:
        orig_patch = R.patch_taxonomy

        def patch_with_ses():
            orig_patch()
            for f in SES:
                sp = R.FT.FEATURE_TAXONOMY[f]
                R.FT.FEATURE_TAXONOMY[f] = R.FeatureSpec(f, R.Mutability.IMMUTABLE, sp.value_range,
                                                         sp.semantic_label + " [frozen post hoc S-P1]")
        R.patch_taxonomy = patch_with_ses

    orig_train = P.train_xgb

    def train_checked(*args, **kw):
        res = orig_train(*args, **kw)
        if s == 42:  # identity with the frozen A2 fit
            ref = pd.read_csv(FROZEN_PROBA)
            got = np.asarray(res["proba"])
            if not np.allclose(ref["proba"].to_numpy(), got, atol=1e-9, rtol=0):
                sys.exit("seed-42 refit differs from the frozen A2 model: stop")
            print("[identity] seed-42 refit equals the frozen A2 test probabilities", flush=True)
        return res
    P.train_xgb = train_checked

    meta = {"tag": a.tag, "posthoc": "S-P1" if a.ses_freeze else "S-P2", "ses_frozen": bool(a.ses_freeze),
            "split_seed": s, "xgboost_random_state": s, "ses_features": SES if a.ses_freeze else []}
    (out / "posthoc_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    if not a.skip_runs:
        sys.argv = ["a2_ckd_runs.py", "--cohort", "main"]
        R.main()
    info = json.loads((out / "a2_runs_main" / "run_info.json").read_text(encoding="utf-8"))
    if str(info.get("status", "")).startswith("NOT REACHED"):
        print(info["status"])
        return
    import a2_ckd_analysis as A
    sys.argv = ["a2_ckd_analysis.py", "--cohort", "main"]
    A.main()


if __name__ == "__main__":
    main()
