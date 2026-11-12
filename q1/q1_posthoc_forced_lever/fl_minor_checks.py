"""Reporting companion to S-P4 (read only, no run): CKD validity under the lock and BMI (v3 review, minor 4).

For the CKD main cohort, DiCE random, configurations frozen (A2) and ses_freeze (S-P1): share of returned
counterfactuals that change BMI (published, lock), validity under the lock with and without a BMI change, and
validity overall per mode. Denominator: all returned counterfactuals (the O-A1 denominator, C11).

Usage (any Python with pandas): python -I fl_minor_checks.py
Output: outputs/q1_posthoc_forced_lever/analysis/ckd_bmi_validity.json
"""
import json
from pathlib import Path

import pandas as pd

O = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs")
SEEDS = (42, 123, 2024, 7, 31337)
RUNS = {"frozen": O / "q1_domain_ckd" / "a2_runs_main",
        "ses_freeze": O / "q1_posthoc_ses_splits" / "ses_freeze" / "a2_runs_main"}


def main():
    res = {"label": "reporting only, read from existing files", "denominator": "all returned counterfactuals"}
    for cfg, base in RUNS.items():
        r = {}
        for mode in ("published", "lock", "route"):
            d = pd.concat([pd.read_csv(base / f"dice_{mode}_seed{s}.csv") for s in SEEDS]).fillna({"changed": ""})
            bmi = d["changed"].str.split(";").apply(lambda s: "BMI" in s)
            r[mode] = {"n": int(len(d)), "share_changing_bmi": float(bmi.mean()), "validity": float(d["valid"].mean()),
                       "validity_if_bmi": float(d.loc[bmi, "valid"].mean()) if bmi.any() else None,
                       "validity_if_not_bmi": float(d.loc[~bmi, "valid"].mean()) if (~bmi).any() else None,
                       "n_bmi": int(bmi.sum())}
        res[cfg] = r
    out = O / "q1_posthoc_forced_lever" / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    (out / "ckd_bmi_validity.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
