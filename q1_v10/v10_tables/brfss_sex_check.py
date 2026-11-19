"""BRFSS 2021: rebuild P7's Kaggle-coded file from P5 (UDSS-MD 0.2.1) in raw-file order and find the Sex source.

Checks
 1. Rebuild the 22 Kaggle columns from P5 0.2.1 (as validate_brfss_kaggle.py in the P5 repo), keep raw-file order,
    drop incomplete rows -> compare with P7's cdc_brfss_diabetes_2021.csv ROW BY ROW (same order expected).
 2. Read SEXVAR, BIRTHSEX and _SEX from the CDC LLCP2021.XPT (read only) and test which one reproduces P7's Sex.
Writes brfss_sex_check.json and frames/brfss2021_p5.csv (P5 coding, SEXVAR) in this folder. Read only elsewhere.
Usage (p7-carla312 venv): python -I brfss_sex_check.py
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
P5 = Path("D:/20-study/uit/research/diabetesxai/paper5/data")
P5_BRFSS = P5 / "harmonized" / "udss_md_brfss_v0.2.1.parquet"
P5_SHA = "7bbfbf0a6157895682d75c9b867504ea853f8643ac41a307f98e37538d4e302c"
XPT = P5 / "raw" / "brfss" / "2021" / "LLCP2021.XPT"
P7_FILE = Path("C:/Repos/uit/diabetes-xai-counterfactual/data/cdc_brfss_diabetes_2021.csv")
KAGGLE = {
    "Diabetes_binary": "diabetes_self", "HighBP": "hypertension_self", "HighChol": "dyslipidemia_self",
    "CholCheck": "cholesterol_check_5y", "BMI": "bmi_self", "Smoker": "smoker_100cig", "Stroke": "stroke_self",
    "HeartDiseaseorAttack": "chd_mi_self", "PhysActivity": "pa_ltpa_any", "Fruits": "fruit_daily",
    "Veggies": "vegetable_daily", "HvyAlcoholConsump": "heavy_drinking", "AnyHealthcare": "health_insurance",
    "NoDocbcCost": "cost_barrier_doctor_12m", "GenHlth": "general_health", "MentHlth": "mental_unhealthy_days_30d",
    "PhysHlth": "physical_unhealthy_days_30d", "DiffWalk": "difficulty_walking", "Sex": "sex", "Age": "age_group",
    "Education": "education_6", "Income": "household_income_11",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    if os.name == "nt":
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    assert sha(P5_BRFSS) == P5_SHA, "P5 BRFSS 0.2.1 hash differs"
    b = pd.read_parquet(P5_BRFSS)
    b = b[b.release.astype(str) == "2021"].reset_index(drop=True)
    k = pd.DataFrame({n: pd.to_numeric(b[c], errors="coerce").astype(float) for n, c in KAGGLE.items()})
    k["BMI"] = k.BMI.round(0)
    k["Sex"] = k.Sex.map({1.0: 1.0, 2.0: 0.0})
    k["_record_id"] = b.record_id.astype(str)
    a = pd.read_csv(P7_FILE).astype(float)
    cols = list(a.columns)
    keep = k[cols].notna().all(axis=1)
    kk = k[keep].reset_index(drop=True)
    res = {"p5_file": str(P5_BRFSS), "p5_sha256": P5_SHA, "p7_file": str(P7_FILE), "p7_sha256": sha(P7_FILE),
           "n_p7": len(a), "n_p5_rebuilt": len(kk)}
    same_n = len(a) == len(kk)
    res["same_row_count"] = same_n
    if same_n:
        diff = (a[cols].values != kk[cols].values)
        res["rows_identical_in_order"] = int((~diff.any(axis=1)).sum())
        res["cells_differing_by_column"] = {c: int(diff[:, i].sum()) for i, c in enumerate(cols)}
        res["rows_differing_only_in_sex"] = int((diff.any(axis=1) & (diff.sum(axis=1) == 1) & diff[:, cols.index("Sex")]).sum())
    # 2. raw sex variables
    raw = pd.read_sas(XPT, format="xport", encoding="latin-1")
    raw = raw[["_STATE", "SEQNO", "SEXVAR", "BIRTHSEX", "_SEX"]].copy()
    raw["SEQNO"] = pd.to_numeric(raw.SEQNO).astype("int64")
    raw["_STATE"] = pd.to_numeric(raw._STATE).astype("int64")
    raw["key"] = "BRFSS_2021_" + raw._STATE.astype(str).str.zfill(2) + "_" + raw.SEQNO.astype(str)
    res["raw_rows"] = len(raw)
    res["record_id_example_p5"] = kk._record_id.iloc[0]
    m = kk[["_record_id"]].merge(raw, left_on="_record_id", right_on="key", how="left")
    res["p5_rows_matched_to_raw"] = int(m.key.notna().sum())
    if same_n and res["p5_rows_matched_to_raw"] == len(kk):
        for v in ("SEXVAR", "_SEX"):
            s = m[v].map({1.0: 1.0, 2.0: 0.0}).values
            res[f"p7_sex_equals_{v}"] = int((s == a.Sex.values).sum())
        dd = a.Sex.values != kk.Sex.values
        sub = m[dd]
        res["differing_rows_birthsex_counts"] = {str(x): int(n) for x, n in sub.BIRTHSEX.value_counts(dropna=False).items()}
        res["differing_rows_sexvar_vs__sex"] = {f"{int(x)}->{int(y)}": int(n) for (x, y), n in
                                                sub.groupby(["SEXVAR", "_SEX"]).size().items()}
        res["all_rows_sexvar_ne__sex"] = int((raw.SEXVAR != raw._SEX).sum())
    out = HERE / "frames"
    out.mkdir(exist_ok=True)
    p = out / "brfss2021_p5.csv"
    kk[cols].to_csv(p, index=False, lineterminator="\n", float_format="%.1f")
    res["frame_p5"] = {"path": str(p), "sha256": sha(p), "n": len(kk)}
    (HERE / "brfss_sex_check.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
