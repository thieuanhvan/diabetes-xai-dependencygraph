"""Environment check before the BRFSS re-runs: refit P7's BRFSS XGBoost on the v9 input file through the v9 loader
and training function, and compare with the stored v9 model (q1_ext_b/models/xgb: test AUC 0.823318976585703,
1,798 eligible, test probabilities). Then fit the same model on the P5 frame (Sex = SEXVAR) and report the change.
Read only outside p5_v10. Usage: <venv>/python -I repro_brfss.py  -> repro_brfss_<venv tag>.json
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "D:/evisyn/projects/diabetesxai/paper7/tools/crossdataset_p4")
import p7_cross_p4pipeline as P  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

O = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs")


def fit(X, y):
    P.seed_everything(P.CFG["random"]["seed"])
    Xtr, Xte, ytr, yte = P.get_train_test_split(X, y, test_size=P.CFG["split"]["test_size"], seed=P.CFG["random"]["seed"],
                                                stratify=P.CFG["split"]["stratify"])
    res = P.train_xgb(Xtr, ytr, Xte, yte, P.XGBConfig(**P.CFG["xgboost"]))
    pr = np.asarray(res["proba"])
    return Xte.index.to_numpy(), pr, float(roc_auc_score(yte, pr)), int((pr >= 0.5).sum())


def main():
    tag = sys.argv[1]
    X, y, _ = P.load("brfss2021")
    idx, pr, auc, el = fit(X, y)
    ref = pd.read_csv(O / "q1_ext_b" / "models" / "xgb" / "test_proba.csv")
    out = {"venv": sys.executable, "v9_file": {"auc": auc, "eligible": el,
           "same_test_index": bool((ref.test_index.to_numpy() == idx).all()),
           "max_abs_diff_proba_vs_stored": float(np.abs(ref.proba1.to_numpy() - pr).max())}}
    d = pd.read_csv(HERE / "frames" / "brfss2021_p5.csv")
    y5 = d[P.TARGET].astype(int)
    X5 = d.drop(columns=[P.TARGET]).astype(float)
    idx5, pr5, auc5, el5 = fit(X5, y5)
    top = lambda p: set(np.argsort(p)[-200:])  # noqa: E731
    out["p5_frame"] = {"auc": auc5, "eligible": el5, "same_test_index": bool((idx5 == idx).all()),
                       "max_abs_diff_proba_vs_v9": float(np.abs(pr5 - pr).max()),
                       "top200_overlap_with_v9": len(top(pr) & top(pr5))}
    (HERE / f"repro_brfss_{tag}.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
