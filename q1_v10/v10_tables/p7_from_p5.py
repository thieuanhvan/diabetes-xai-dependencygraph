"""P7 analysis frames read from P5 (UDSS-MD 0.2.1) instead of P7's own NHANES and BRFSS recoding (re-analysis v10).

Extended copy of p5_migration/p7_from_p5.py (0.2.0 measurement run, left unchanged): input is now the 0.2.1 release,
only the variant p5 is written (the v9 coding is kept as the stored v9 outputs), every NHANES frame is compared
byte for byte with the 0.2.0 frame of the measurement run, and the BRFSS 2021 frame (Kaggle coding, Sex = SEXVAR) is
added (build_brfss). NHIS is not built: P5 0.2.1 lacks four of P7's NHIS inputs (see the deviation note).
Nothing in P5, in the P7 repositories or in existing P7 outputs is written.

Coding comes from P5 columns; P7's own inclusion rules stay here, in P7 code:
  CKD / HTN / matched DM: age >= 20, examined (exam_status 2), not pregnant, label available, complete cases.
  Table 4 NHANES diabetes: age >= 20, complete cases on the 14 features + diabetes_self + HbA1c (as p7_cross_p4pipeline).

Variants of every frame:
  p5        all coding from P5, PhysActivity = pa_meets_guideline (leisure >= 150 min/week, both cycles)
  p5_p7pa   as p5, but PhysActivity = P7's own variable (2017-2020 PAQ605 work activity; 2021-2023 gpaq_v2),
            rebuilt read-only with the nhanes-diabetes recoders. Used only to split the change into
            'PhysActivity' and 'everything else'.
P5 columns are mapped onto P7's codes where P7 used a different scale (Sex 1/0, Income 5 PIR bands,
MentHlth PHQ-9 bands, Education BRFSS EDUCA scale). P5 Education has 4 levels (DMDEDUC2 1 and 2 merged), so
P7 levels 2 and 3 cannot be told apart: P5 level 1 is written as 3 (see the report).

Usage (p7-carla312 venv):  python -I p7_from_p5.py          -> frames/ + frame_comparison.json/.md
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
P5_DATA = Path("D:/20-study/uit/research/diabetesxai/paper5/data/harmonized")
P5_NHANES = P5_DATA / "udss_md_nhanes_v0.2.1.parquet"
P5_SHA256 = "580d01142b7804f857012e5a5818fbfaaf7b62249606ed39e51c35cfc51163e6"
P5_BRFSS = P5_DATA / "udss_md_brfss_v0.2.1.parquet"
P5_BRFSS_SHA256 = "7bbfbf0a6157895682d75c9b867504ea853f8643ac41a307f98e37538d4e302c"
MIG_FRAMES = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_migration/frames")
P7_BRFSS = Path("C:/Repos/uit/diabetes-xai-counterfactual/data/cdc_brfss_diabetes_2021.csv")
P7OUT = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs")
ORIG = {"ckd": P7OUT / "q1_domain_ckd" / "a0_nhanes_ckd" / "nhanes_ckd_analytic_2017-2023.csv",
        "htn": P7OUT / "q1_domain_htn" / "a0_nhanes_htn" / "nhanes_htn_analytic_2017-2023.csv",
        "dm": P7OUT / "q1_posthoc_v5" / "nhanes_dm" / "nhanes_dm_rows_2017-2023.csv"}
NHANES_REPO = Path("C:/Repos/uit/nhanes-diabetes")
NHANES_P7_RAW = NHANES_REPO / "data" / "raw" / "cdc"
FRAMES = HERE / "frames"
CYCLES = {"2017-2020": 0, "2021-2023": 1}

CKD_FEATURES = ["Diabetes", "HighBP", "HighChol", "BMI", "Smoker", "PhysActivity", "GenHlth", "MentHlth", "Stroke",
                "HeartDiseaseorAttack", "Age", "Sex", "Education", "Income", "AnyHealthcare", "Cycle"]
HTN_FEATURES = ["Diabetes", "HighChol", "BMI", "Smoker", "PhysActivity", "GenHlth", "MentHlth", "Stroke",
                "HeartDiseaseorAttack", "KidneyDisease", "Age", "Sex", "Education", "Income", "AnyHealthcare", "Cycle"]
DM_FEATURES = ["HighBP", "HighChol", "BMI", "Smoker", "PhysActivity", "GenHlth", "MentHlth", "Stroke",
               "HeartDiseaseorAttack", "KidneyDisease", "Age", "Sex", "Education", "Income", "AnyHealthcare", "Cycle"]
T4_FEATURES = ["HighBP", "HighChol", "BMI", "Smoker", "Stroke", "HeartDiseaseorAttack", "PhysActivity",
               "AnyHealthcare", "GenHlth", "MentHlth", "Sex", "Age", "Education", "Income"]


def below_normal():
    if os.name == "nt":
        try:
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
        except Exception:
            pass


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def trunc_sig(x, sig=4):
    """Truncate (never round) to `sig` significant digits; text."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "NA"
    if x == 0:
        return "0"
    neg = x < 0
    x = abs(float(x))
    e = math.floor(math.log10(x))
    dec = sig - 1 - e
    f = 10 ** dec
    v = math.floor(x * f + 1e-9) / f
    s = f"{v:.{max(dec, 0)}f}"
    return ("-" if neg else "") + s


# ----------------------------------------------------------------------------------------------- P5 -> P7 codes
def phq_band(score):
    """P7 MentHlth bands of the PHQ-9 total (nhanes-diabetes recode_phq9_to_menthlth)."""
    s = pd.to_numeric(score, errors="coerce").astype(float)
    out = pd.Series(np.nan, index=s.index)
    out[s.between(0, 4)] = 0.0
    out[s.between(5, 9)] = 5.0
    out[s.between(10, 14)] = 10.0
    out[s.between(15, 19)] = 20.0
    out[s >= 20] = 30.0
    return out


def income_band(pir):
    """P7 Income: INDFMPIR in 5 bands (<1, 1-<2, 2-<4, 4-<5, 5)."""
    s = pd.to_numeric(pir, errors="coerce").astype(float)
    out = pd.Series(np.nan, index=s.index)
    out[(s >= 0) & (s < 1)] = 1.0
    out[(s >= 1) & (s < 2)] = 2.0
    out[(s >= 2) & (s < 4)] = 3.0
    out[(s >= 4) & (s < 5)] = 4.0
    out[s >= 5] = 5.0
    return out


EDU_P5_TO_P7 = {1: 3.0, 2: 4.0, 3: 5.0, 4: 6.0}   # P5 1 = DMDEDUC2 1 or 2 (P7 2 or 3) -> 3


def f(s):
    return pd.to_numeric(s, errors="coerce").astype(float)


def load_p5() -> pd.DataFrame:
    if sha256_file(P5_NHANES) != P5_SHA256:
        sys.exit("P5 NHANES parquet hash differs from the 0.2.1 SHA256SUMS")
    d = pd.read_parquet(P5_NHANES)
    return d[d["release"].isin(list(CYCLES))].reset_index(drop=True)


def p7_physactivity() -> pd.DataFrame:
    """P7's own PhysActivity (read-only call of the nhanes-diabetes recoders), for the p5_p7pa variant only."""
    sys.path.insert(0, str(NHANES_REPO / "src"))
    from nhanes_diabetes.encoding.core import build_cycle
    from nhanes_diabetes.encoding.cycle_loader import load_cycle
    parts = []
    for cyc in CYCLES:
        joined, _ = load_cycle(cyc, NHANES_P7_RAW)
        base, prov = build_cycle(joined, cyc)
        parts.append(pd.DataFrame({"SEQN": pd.to_numeric(joined["SEQN"]).astype("int64").values,
                                   "PhysActivity_P7": base["PhysActivity"].values}))
    return pd.concat(parts, ignore_index=True)


def coded(p5: pd.DataFrame, pa7: pd.DataFrame | None) -> pd.DataFrame:
    """Every P7 variable written from P5 columns (P7 codes), one row per NHANES participant."""
    c = pd.DataFrame({"SEQN": p5["respondent_id"].astype("int64")})
    c["Cycle"] = p5["release"].map(CYCLES).astype(float)
    c["Age"] = f(p5["age_years"])
    c["Sex"] = f(p5["sex"]).map({1.0: 1.0, 2.0: 0.0})
    c["BMI"] = f(p5["bmi_measured"]).round(0)
    c["BMI_cont"] = f(p5["bmi_measured"])
    c["Education"] = f(p5["education"]).map(EDU_P5_TO_P7)
    c["Income"] = income_band(p5["income_pir"])
    c["AnyHealthcare"] = f(p5["health_insurance"])
    c["GenHlth"] = f(p5["general_health"])
    c["MentHlth"] = phq_band(p5["phq9_score"])
    c["Stroke"] = f(p5["stroke_self"])
    c["HeartDiseaseorAttack"] = f(p5["chd_mi_self"])
    c["Diabetes"] = f(p5["diabetes_self"])
    ss = f(p5["smoking_status"])
    c["Smoker_current"] = ss.map({0.0: 0.0, 1.0: 0.0, 2.0: 1.0})
    c["Smoker_ever"] = f(p5["smoker_100cig"])
    sbp = f(p5["sbp_mean"])
    c["HighBP_measured"] = np.where(sbp.isna(), np.nan, (sbp >= 130).astype(float))
    c["HighBP_told"] = f(p5["hypertension_self"])
    c["HighChol_measured"] = f(p5["high_tc_measured"])
    c["HighChol_told"] = f(p5["dyslipidemia_self"])
    c["KidneyDisease"] = f(p5["ckd_self"])
    c["PhysActivity"] = f(p5["pa_meets_guideline"])
    c["CKD_label"] = f(p5["ckd_measured"])
    c["HTN_L1_measured"] = f(p5["hypertension_measured_acc"])
    c["HTN_L2_measured_or_treated"] = f(p5["hypertension_total_acc"])   # v10: secondary HTN label (L1 or BP medicine)
    c["BP_med_now"] = f(p5["bp_med_now"])
    hb = f(p5["hba1c_pct"])
    c["HbA1c"] = hb
    c["DM_A1C"] = np.where(hb.isna(), np.nan, (hb >= 6.5).astype(float))
    c["DM_DIAG"] = f(p5["diabetes_self"])
    c["SBP_mean"] = sbp
    c["DBP_mean"] = f(p5["dbp_mean"])
    c["eGFR_ckdepi2021"] = f(p5["egfr_ckdepi2021"])
    c["URDACT"] = f(p5["uacr_mgg"])
    c["WTMEC"] = f(p5["wt_exam"])
    c["SDMVPSU"], c["SDMVSTRA"] = f(p5["svy_psu"]), f(p5["svy_strata"])
    # P7 inclusion inputs (filters are applied in build_*, not here)
    c["_exam"] = f(p5["exam_status"])
    c["_pregnant"] = f(p5["pregnant"])
    if pa7 is not None:
        c = c.merge(pa7, on="SEQN", how="left", validate="one_to_one")
        c["PhysActivity"] = c.pop("PhysActivity_P7")
    return c


def base_filter(c):
    return c[(c.Age >= 20) & (c._exam == 2) & (c._pregnant != 1)]


def build_ckd(c):
    d = base_filter(c).copy()
    d["HighBP"], d["HighChol"], d["Smoker"] = d.HighBP_measured, d.HighChol_measured, d.Smoker_current
    d["KIQ022_weakfailingkidneys"] = d.KidneyDisease
    d["BPQ020_toldHighBP"], d["BPQ080_toldHighChol"] = d.HighBP_told, d.HighChol_told
    d = d[d.CKD_label.notna()]
    d = d[d[CKD_FEATURES].notna().all(axis=1)]
    cols = ["SEQN", "CKD_label"] + CKD_FEATURES + ["BPQ020_toldHighBP", "BPQ080_toldHighChol", "KIQ022_weakfailingkidneys",
                                                  "WTMEC", "SDMVPSU", "SDMVSTRA", "SBP_mean", "eGFR_ckdepi2021", "URDACT"]
    d = d[cols].sort_values(["Cycle", "SEQN"]).reset_index(drop=True)
    for k in ["CKD_label"] + CKD_FEATURES:
        d[k] = d[k].astype(int)
    return d


def build_htn(c):
    d = base_filter(c).copy()
    d["HighChol"], d["Smoker"] = d.HighChol_measured, d.Smoker_current
    d["BPQ020_toldHighBP"], d["BPQ080_toldHighChol"] = d.HighBP_told, d.HighChol_told
    d = d[d.HTN_L1_measured.notna()]
    d = d[d[HTN_FEATURES].notna().all(axis=1)]
    cols = ["SEQN", "HTN_L1_measured"] + HTN_FEATURES + ["BPQ020_toldHighBP", "BPQ080_toldHighChol", "WTMEC", "SDMVPSU",
                                                        "SDMVSTRA", "SBP_mean", "DBP_mean"]
    d = d[cols].sort_values(["Cycle", "SEQN"]).reset_index(drop=True)
    for k in ["HTN_L1_measured"] + HTN_FEATURES:
        d[k] = d[k].astype(int)
    return d


def build_htn_ext(c):
    """v10: the HTN frame with the two columns the secondary variants need (l2 label, no_bpmed cohort).
    Rows, order and the main-variant columns equal build_htn (checked in main)."""
    d = base_filter(c).copy()
    d["HighChol"], d["Smoker"] = d.HighChol_measured, d.Smoker_current
    d["BPQ020_toldHighBP"], d["BPQ080_toldHighChol"] = d.HighBP_told, d.HighChol_told
    d = d[d.HTN_L1_measured.notna()]
    d = d[d[HTN_FEATURES].notna().all(axis=1)]
    cols = ["SEQN", "HTN_L1_measured", "HTN_L2_measured_or_treated"] + HTN_FEATURES + [
        "BPQ020_toldHighBP", "BPQ080_toldHighChol", "BP_med_now", "WTMEC", "SDMVPSU", "SDMVSTRA", "SBP_mean", "DBP_mean"]
    d = d[cols].sort_values(["Cycle", "SEQN"]).reset_index(drop=True)
    for k in ["HTN_L1_measured"] + HTN_FEATURES:
        d[k] = d[k].astype(int)
    d["HTN_L2_measured_or_treated"] = d["HTN_L2_measured_or_treated"].astype("Int64")
    return d


def build_dm(c):
    """Rows of the matched DM arm (complete cases are taken per variant in v5_dm_runs.py, as in P7)."""
    d = base_filter(c).copy()
    d["HighBP"], d["HighChol"], d["Smoker"] = d.HighBP_told, d.HighChol_measured, d.Smoker_current
    d = d[d.DM_A1C.notna() | d.DM_DIAG.notna()]
    cols = ["SEQN"] + DM_FEATURES + ["HighBP_measured", "DM_A1C", "DM_DIAG", "HbA1c"]
    cols = list(dict.fromkeys(cols))
    return d[cols].sort_values(["Cycle", "SEQN"]).reset_index(drop=True)


def build_t4(c, cycle):
    """Table 4 NHANES diabetes frame (p7_cross_p4pipeline.load): Teboul names, told HighBP/HighChol, ever smoker."""
    d = c[c.Cycle == CYCLES[cycle]].copy()
    d["HighBP"], d["HighChol"], d["Smoker"] = d.HighBP_told, d.HighChol_told, d.Smoker_ever
    d["Diabetes_self"] = d.Diabetes
    d["BMI"] = d.BMI_cont   # the pipeline rounds BMI itself
    d = d[d.Age >= 20].dropna(subset=T4_FEATURES + ["Diabetes_self", "HbA1c"])
    return d[["SEQN"] + T4_FEATURES + ["Diabetes_self", "HbA1c"]].reset_index(drop=True)


KAGGLE = {
    "Diabetes_binary": "diabetes_self", "HighBP": "hypertension_self", "HighChol": "dyslipidemia_self",
    "CholCheck": "cholesterol_check_5y", "BMI": "bmi_self", "Smoker": "smoker_100cig", "Stroke": "stroke_self",
    "HeartDiseaseorAttack": "chd_mi_self", "PhysActivity": "pa_ltpa_any", "Fruits": "fruit_daily",
    "Veggies": "vegetable_daily", "HvyAlcoholConsump": "heavy_drinking", "AnyHealthcare": "health_insurance",
    "NoDocbcCost": "cost_barrier_doctor_12m", "GenHlth": "general_health", "MentHlth": "mental_unhealthy_days_30d",
    "PhysHlth": "physical_unhealthy_days_30d", "DiffWalk": "difficulty_walking", "Sex": "sex", "Age": "age_group",
    "Education": "education_6", "Income": "household_income_11",
}


def build_brfss():
    """BRFSS 2021 in P7's Kaggle coding from P5 0.2.1, raw-file order, listwise deletion (P5 validate_brfss_kaggle rule).
    Sex = P5 `sex` (SEXVAR); P7 v9 used the CDC calculated _SEX (see brfss_sex_check.json)."""
    if sha256_file(P5_BRFSS) != P5_BRFSS_SHA256:
        sys.exit("P5 BRFSS parquet hash differs from the 0.2.1 SHA256SUMS")
    b = pd.read_parquet(P5_BRFSS)
    b = b[b.release.astype(str) == "2021"].reset_index(drop=True)
    k = pd.DataFrame({n: f(b[c]) for n, c in KAGGLE.items()})
    k["BMI"] = k.BMI.round(0)
    k["Sex"] = k.Sex.map({1.0: 1.0, 2.0: 0.0})
    return k[k.notna().all(axis=1)].reset_index(drop=True)


# ----------------------------------------------------------------------------------------------- comparison
def compare(new: pd.DataFrame, old: pd.DataFrame, cols, key="SEQN") -> dict:
    a, b = set(old[key]), set(new[key])
    m = old.merge(new, on=key, suffixes=("_v9", "_p5"))
    out = {"n_v9": len(old), "n_p5": len(new), "rows_only_v9": len(a - b), "rows_only_p5": len(b - a),
           "rows_both": len(m), "value_mismatch_on_common_rows": {}}
    for col in cols:
        x, y = m[f"{col}_v9"].astype(float), m[f"{col}_p5"].astype(float)
        out["value_mismatch_on_common_rows"][col] = int(((x - y).abs() > 1e-9).sum() + (x.isna() != y.isna()).sum())
    return out


def main():
    below_normal()
    FRAMES.mkdir(parents=True, exist_ok=True)
    p5 = load_p5()
    res = {"p5_file": str(P5_NHANES), "p5_sha256": P5_SHA256, "p5_repo_commit": "3b1809f", "frames": {},
           "identical_to_0_2_0_frame": {}}
    c = coded(p5, None)
    built = {"ckd": build_ckd(c), "htn": build_htn(c), "dm": build_dm(c)}
    for cyc in CYCLES:
        built[f"t4_{cyc}"] = build_t4(c, cyc)
    for k, d in built.items():
        p = FRAMES / f"{k}_p5.csv"
        d.to_csv(p, index=False, lineterminator="\n", float_format="%.6f")
        h = sha256_file(p)
        res["frames"][f"{k}_p5"] = {"path": str(p), "n": len(d), "sha256": h}
        res["identical_to_0_2_0_frame"][k] = h == sha256_file(MIG_FRAMES / f"{k}_p5.csv")
    he = build_htn_ext(c)
    m = built["htn"]
    assert m.SEQN.equals(he.SEQN) and all(m[col].equals(he[col]) for col in m.columns), "htn_ext differs from htn"
    p = FRAMES / "htn_ext_p5.csv"
    he.to_csv(p, index=False, lineterminator="\n", float_format="%.6f")
    res["frames"]["htn_ext_p5"] = {"path": str(p), "n": len(he), "sha256": sha256_file(p),
                                   "note": "htn_p5 plus HTN_L2_measured_or_treated (P5 hypertension_total_acc) and BP_med_now"}
    br = build_brfss()
    p = FRAMES / "brfss2021_p5.csv"
    br.to_csv(p, index=False, lineterminator="\n", float_format="%.1f")
    a = pd.read_csv(P7_BRFSS).astype(float)
    diff = a[list(a.columns)].values != br[list(a.columns)].values
    res["frames"]["brfss2021_p5"] = {"path": str(p), "n": len(br), "sha256": sha256_file(p), "p5_file": str(P5_BRFSS),
                                     "p5_sha256": P5_BRFSS_SHA256}
    res["brfss_vs_v9_file"] = {"n_v9": len(a), "same_order_rows_identical": int((~diff.any(axis=1)).sum()),
                               "cells_differing": {col: int(diff[:, i].sum()) for i, col in enumerate(a.columns) if diff[:, i].any()}}
    (HERE / "frame_manifest.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
