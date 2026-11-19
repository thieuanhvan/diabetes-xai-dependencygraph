"""Classifier robustness for the P7 journal version (FAIR reviewer B): rerun the audit and the two
enforcement modes with Logistic Regression and Random Forest instead of XGBoost.

Everything except the classifier is the locked pipeline: loaders, split (seed 42, stratified 80/20),
cohort rule (p >= 0.5, top 200), taxonomy patches, DiCE seeds, regeneration budget and the exhaustive
search come from p7_cross_p4pipeline.py and p7_cross_exhaustive.py. The classifier is swapped by
replacing the training function those scripts call.

Usage (P4 venv, isolated mode):
  python -I p7_cross_classifiers.py --clf lr --gen random --dataset brfss2021 --tag _lr
  python -I p7_cross_classifiers.py --clf rf --gen exhaustive --dataset nhis2022 --tag _rf_exh
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _pop(flag):
    i = sys.argv.index(flag)
    v = sys.argv[i + 1]
    del sys.argv[i:i + 2]
    return v


CLF = _pop("--clf")
GEN = _pop("--gen")

import numpy as np  # noqa: E402
import p7_cross_p4pipeline as P  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402


def train_alt(Xtr, ytr, Xte, yte, _cfg):
    if CLF == "lr":
        # Standardised inputs, L2 penalty at the sklearn default strength; no tuning, as for XGBoost.
        model = Pipeline([("scale", StandardScaler()),
                          ("lr", LogisticRegression(max_iter=5000, random_state=42))])
    elif CLF == "rf":
        # sklearn defaults (100 fully grown trees), no tuning, as for the other two classifiers.
        # Larger leaves gave smoother but less extreme probabilities and left almost no patient
        # with p >= 0.5 on the NHANES cohorts (checked 11/11/2026), so the defaults were kept.
        model = RandomForestClassifier(n_jobs=2, random_state=42)
    else:
        raise ValueError(CLF)
    model.fit(Xtr, ytr)
    if CLF == "rf":
        model.set_params(n_jobs=1)  # DiCE scores small batches; thread start-up costs more than it saves
    return {"model": model, "proba": model.predict_proba(Xte)[:, 1]}


P.train_xgb = train_alt

if __name__ == "__main__":
    if GEN == "random":
        P.main()
    elif GEN == "exhaustive":
        import p7_cross_exhaustive as E
        E.main()
    else:
        raise ValueError(GEN)
