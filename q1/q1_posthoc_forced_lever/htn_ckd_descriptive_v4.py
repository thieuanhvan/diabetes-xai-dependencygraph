"""Descriptive check for the v4 article (read only, no run): why the actionability error is rare in hypertension.

For the hypertension main run (L1, R-IMM, DiCE random, published and lock) and, for comparison, the CKD main cohort
in both configurations (S-P1 ses_freeze, A2 frozen), it reports over all returned counterfactuals:
share that changes BMI, share that touches an indicator, the primary metric (no action: change set not empty and
without any lever or treatable), share with an empty change set; and the XGBoost gain shares of BMI and of the
indicators (GenHlth, MentHlth) read from the saved model files. Patient means (unit of Section 3.8) and pooled.
This is an explanation checked descriptively, not a test.

Usage (any Python with pandas): python -I htn_ckd_descriptive_v4.py
Output: outputs/journal_main/htn_ckd_descriptive_v4.json
"""
import json
from pathlib import Path

import pandas as pd

O = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs")
SEEDS = (42, 123, 2024, 7, 31337)
ACTION = {"BMI", "Smoker", "PhysActivity", "HighBP", "HighChol"}
IND = {"GenHlth", "MentHlth"}
RUNS = {"htn_main": O / "q1_domain_htn" / "a2_runs_main",
        "ckd_ses_freeze": O / "q1_posthoc_ses_splits" / "ses_freeze" / "a2_runs_main",
        "ckd_frozen": O / "q1_domain_ckd" / "a2_runs_main"}
MODELS = {"htn_main": O / "q1_domain_htn" / "a2_model" / "xgb_htn.json",
          "ckd": O / "q1_domain_ckd" / "a2_model" / "xgb_ckd.json"}


def trunc(x, k=4):
    return int(x * 10 ** k) / 10 ** k


def gain_shares(path):
    import xgboost as xgb
    b = xgb.Booster()
    b.load_model(str(path))
    g = b.get_score(importance_type="total_gain")
    tot = sum(g.values())
    return {f: trunc(v / tot) for f, v in sorted(g.items(), key=lambda kv: -kv[1])}


def main():
    res = {"label": "descriptive, read from existing files", "denominator": "all returned counterfactuals"}
    for name, base in RUNS.items():
        r = {}
        for mode in ("published", "lock"):
            d = pd.concat([pd.read_csv(base / f"dice_{mode}_seed{s}.csv") for s in SEEDS]).fillna({"changed": ""})
            S = d["changed"].str.split(";").apply(lambda s: {x for x in s if x})
            d["bmi"] = S.apply(lambda s: "BMI" in s)
            d["touch"] = S.apply(lambda s: bool(s & IND))
            d["no_action"] = S.apply(lambda s: bool(s) and not (s & ACTION))
            d["empty"] = S.apply(lambda s: not s)
            cols = ["bmi", "touch", "no_action", "empty", "valid"]
            pm = d.groupby("pid")[cols].mean()
            r[mode] = {"n_cf": int(len(d)), "n_patients": int(pm.shape[0]),
                       "patient_mean": {c: trunc(float(pm[c].mean())) for c in cols},
                       "pooled": {c: trunc(float(d[c].mean())) for c in cols}}
        res[name] = r
    try:
        res["gain_share"] = {k: gain_shares(p) for k, p in MODELS.items()}
    except Exception as e:  # xgboost missing in this interpreter
        res["gain_share"] = f"not computed: {e}"
    out = O / "journal_main"
    out.mkdir(parents=True, exist_ok=True)
    (out / "htn_ckd_descriptive_v4.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
