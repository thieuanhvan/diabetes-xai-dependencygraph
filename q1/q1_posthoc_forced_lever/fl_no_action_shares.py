"""Reporting companion to S-P4 (read only, no run): the primary actionability metric of the v4 article in CKD.

No action = the change set is not empty and contains no lever and no treatable feature (it moves indicators,
socio-economic features or both). Empty change sets (the counterfactual rounds back to the patient) stay in the
denominator and are reported separately as "empty". Computed for DiCE random in the CKD main cohort, configurations frozen (A2) and
ses_freeze (S-P1), modes published, lock, route and, when present, the S-P4 forced mode. Denominator: all returned
counterfactuals, valid or not. Reported both as the patient mean (patients with at least one returned
counterfactual, the unit of Section 3.8) and pooled over counterfactuals.

Roles (derived CKD role table): levers BMI, Smoker, PhysActivity; treatable HighBP, HighChol; indicators GenHlth,
MentHlth; socio-economic Education, Income, AnyHealthcare.

Usage (any Python with pandas): python -I fl_no_action_shares.py
Output: outputs/q1_posthoc_forced_lever/analysis/ckd_no_action_shares.json
"""
import json
from pathlib import Path

import pandas as pd

O = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs")
SEEDS = (42, 123, 2024, 7, 31337)
RUNS = {"frozen": {"published": O / "q1_domain_ckd" / "a2_runs_main",
                   "lock": O / "q1_domain_ckd" / "a2_runs_main",
                   "route": O / "q1_domain_ckd" / "a2_runs_main",
                   "forced": O / "q1_posthoc_forced_lever" / "ckd_frozen"},
        "ses_freeze": {"published": O / "q1_posthoc_ses_splits" / "ses_freeze" / "a2_runs_main",
                       "lock": O / "q1_posthoc_ses_splits" / "ses_freeze" / "a2_runs_main",
                       "route": O / "q1_posthoc_ses_splits" / "ses_freeze" / "a2_runs_main",
                       "forced": O / "q1_posthoc_forced_lever" / "ckd_ses_freeze"}}
ACTION = {"BMI", "Smoker", "PhysActivity", "HighBP", "HighChol"}
IND = {"GenHlth", "MentHlth"}
SES = {"Education", "Income", "AnyHealthcare"}


def trunc(x, k=4):
    return None if x is None else int(x * 10 ** k) / 10 ** k


def main():
    res = {"label": "reporting only, read from existing files", "denominator": "all returned counterfactuals",
           "metric": "no lever and no treatable change"}
    for cfg, modes in RUNS.items():
        r = {}
        for mode, base in modes.items():
            files = [base / f"dice_{mode}_seed{s}.csv" for s in SEEDS]
            if not all(f.exists() for f in files):
                r[mode] = "not available"
                continue
            d = pd.concat([pd.read_csv(f) for f in files]).fillna({"changed": ""})
            S = d["changed"].str.split(";").apply(lambda s: {x for x in s if x})
            d["no_action"] = S.apply(lambda s: bool(s) and not (s & ACTION))
            d["fully"] = S.apply(lambda s: bool(s & IND) and not (s & ACTION))
            d["ses_only"] = S.apply(lambda s: bool(s) and s <= SES)
            d["empty"] = S.apply(lambda s: not s)
            pm = d.groupby("pid")[["no_action", "fully", "ses_only", "empty", "valid"]].mean()
            r[mode] = {"n_cf": int(len(d)), "n_patients": int(pm.shape[0]),
                       "patient_mean": {c: trunc(float(pm[c].mean())) for c in pm.columns},
                       "pooled": {c: trunc(float(d[c].mean())) for c in ("no_action", "fully", "ses_only", "empty", "valid")}}
        res[cfg] = r
    out = O / "q1_posthoc_forced_lever" / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    (out / "ckd_no_action_shares.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
