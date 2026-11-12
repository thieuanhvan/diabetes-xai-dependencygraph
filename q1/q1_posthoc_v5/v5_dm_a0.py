"""POST HOC (S-P5), matched three-disease comparison: NHANES diabetes table and role table (plan Section 6).

Same cycles, raw files and recoders as A0-CKD and A0-HTN (`load_cycle` + `build_cycle` of the nhanes-diabetes
repository; extra tables TCHOL and KIQ_U from paper7/data_q1/nhanes_raw/). No model is fitted here.

Labels (the rule of the P7 NHANES diabetes tables, read from tools/crossdataset_p4/p7_cross_p4pipeline.py, which
uses `HbA1c >= 6.5` for the 'a1c' label and `Diabetes_self` (DIQ010 = 1, borderline = 0) for the 'diag' label):
  DM_A1C  = 1 if LBXGH >= 6.5 %, 0 if below, missing if HbA1c missing          (primary)
  DM_DIAG = Diabetes_self of build_cycle                                       (secondary)
Features (16) = HTN schema with Diabetes (outcome concept, rule R-OUT) replaced by HighBP:
  HighBP = BPQ020 told high blood pressure (build_cycle 'HighBP'); HighChol = LBXTC >= 240 mg/dL (measured, as CKD/HTN);
  Smoker = current smoking (SMQ020/SMQ040, as CKD/HTN); KidneyDisease = KIQ022; BMI integer; the rest from build_cycle.
  Auxiliary (variant dm_hbp_measured): HighBP_measured = mean BPXOSY1-3 >= 130 mmHg (the CKD definition).
Rows kept: age >= 20, RIDSTATR = 2, RIDEXPRG != 1, at least one label available. Complete cases are taken per variant
in v5_dm_runs.py (flow written there).
Role table: derived by the A0-HTN rule (inherit the diabetes RoleAssignment of the Concept from the P7 KG export,
otherwise the fixed concept-class rule; R-IMM), written and hashed before any model.
Usage (p7-carla312 venv): python -I v5_dm_a0.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS / "q1_domain_htn"))
sys.path.insert(0, str(TOOLS / "q1_domain_ckd"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from htn_common import (NHANES_NEW_RAW, NHANES_P7_RAW, NHANES_REPO, P7_REPO, PAPER7, below_normal, check_prereg,  # noqa: E402
                        sha256_file, trunc, write_json)

sys.path.insert(0, str(NHANES_REPO / "src"))
sys.path.insert(0, str(P7_REPO / "src"))
from nhanes_diabetes.encoding.core import build_cycle  # noqa: E402
from nhanes_diabetes.encoding.cycle_loader import load_cycle, read_xpt  # noqa: E402
from a0_nhanes_ckd import yes_no  # noqa: E402
from depgraph.nodes import DIRECTION, TIER  # noqa: E402

OUT = PAPER7 / "outputs" / "q1_posthoc_v5" / "nhanes_dm"
KG_NODES = PAPER7 / "outputs" / "kg_export" / "dependency_graph_nodes.csv"
DOMAIN = "Diabetes mellitus (MONDO:0005015), NHANES matched arm"
CYCLES = {"2017-2020": {"code": 0, "files": {"TCHOL": "P_TCHOL", "KIQ_U": "P_KIQ_U"}},
          "2021-2023": {"code": 1, "files": {"TCHOL": "TCHOL_L", "KIQ_U": "KIQ_U_L"}}}
FEATURES = ["HighBP", "HighChol", "BMI", "Smoker", "PhysActivity", "GenHlth", "MentHlth", "Stroke",
            "HeartDiseaseorAttack", "KidneyDisease", "Age", "Sex", "Education", "Income", "AnyHealthcare", "Cycle"]
SBP = ["BPXOSY1", "BPXOSY2", "BPXOSY3"]

MEASURES_BRFSS = {  # identical to q1_domain_htn/a0_role_table_htn.py
    "HighBP": "BLOOD_PRESSURE", "HighChol": "CHOLESTEROL", "BMI": "BODY_WEIGHT", "Smoker": "SMOKING",
    "PhysActivity": "PHYSICAL_ACTIVITY", "Fruits": "FRUIT_INTAKE", "Veggies": "VEGETABLE_INTAKE",
    "HvyAlcoholConsump": "ALCOHOL", "NoDocbcCost": "COST_BARRIER", "GenHlth": "GENERAL_HEALTH",
    "MentHlth": "MENTAL_HEALTH", "PhysHlth": "PHYSICAL_FUNCTION", "DiffWalk": "MOBILITY", "Age": "AGE", "Sex": "SEX",
    "Stroke": "STROKE_HISTORY", "HeartDiseaseorAttack": "CHD_MI_HISTORY", "Income": "INCOME", "Education": "EDUCATION",
    "AnyHealthcare": "HEALTH_COVERAGE", "CholCheck": "CHOLESTEROL_CHECK",
}
MEASURES_DM = {
    "HighBP": ("HYPERTENSION_DIAGNOSIS_HISTORY", "BPQ020 = 1 (ever told high blood pressure)"),
    "HighChol": ("CHOLESTEROL", "LBXTC >= 240 mg/dL (measured)"),
    "BMI": ("BODY_WEIGHT", "BMXBMI, integer"),
    "Smoker": ("SMOKING", "SMQ020 = 1 and SMQ040 in {1, 2} (current)"),
    "PhysActivity": ("PHYSICAL_ACTIVITY", "2017-2020 PAQ605; 2021-2023 gpaq_v2"),
    "GenHlth": ("GENERAL_HEALTH", "HUQ010"),
    "MentHlth": ("MENTAL_HEALTH", "PHQ-9 total in P7 bands"),
    "Stroke": ("STROKE_HISTORY", "MCQ160F"),
    "HeartDiseaseorAttack": ("CHD_MI_HISTORY", "MCQ160C or MCQ160E"),
    "KidneyDisease": ("KIDNEY_DISEASE_HISTORY", "KIQ022 = 1"),
    "Age": ("AGE", "RIDAGEYR"), "Sex": ("SEX", "RIAGENDR"), "Education": ("EDUCATION", "DMDEDUC2"),
    "Income": ("INCOME", "INDFMPIR, 5 bands"), "AnyHealthcare": ("HEALTH_COVERAGE", "HIQ011"),
    "Cycle": ("SURVEY_CYCLE", "0 = 2017-2020, 1 = 2021-2023"),
}
OUTCOME_CONCEPTS = {"GLYCAEMIA", "DIABETES_HISTORY"}  # R-OUT: DIQ010 (Diabetes) is not a feature
RULE = {"diagnosis_history": "immutable", "demographic": "immutable", "survey_design": "immutable",
        "behaviour": "lever", "measured_clinical_risk_factor": "treatable", "patient_reported_health_status": "indicator"}
NEW_CONCEPT_CLASS = {"HYPERTENSION_DIAGNOSIS_HISTORY": "diagnosis_history", "KIDNEY_DISEASE_HISTORY": "diagnosis_history",
                     "SURVEY_CYCLE": "survey_design"}
EXPECTED = {"HighBP": ("immutable", "immutable"), "HighChol": ("treatable", "monotonic_down"),
            "BMI": ("lever", "bidirectional"), "Smoker": ("lever", "monotonic_down"),
            "PhysActivity": ("lever", "monotonic_up"), "GenHlth": ("indicator", "monotonic_down"),
            "MentHlth": ("indicator", "monotonic_down"), "Stroke": ("immutable", "immutable"),
            "HeartDiseaseorAttack": ("immutable", "immutable"), "KidneyDisease": ("immutable", "immutable"),
            "Age": ("immutable", "immutable"), "Sex": ("immutable", "immutable"), "Education": ("immutable", "immutable"),
            "Income": ("immutable", "immutable"), "AnyHealthcare": ("immutable", "immutable"),
            "Cycle": ("immutable", "immutable")}


def derive_roles():
    kg = {r["node"]: r for r in csv.DictReader(open(KG_NODES, encoding="utf-8"))}
    assert set(kg) == set(TIER) == set(MEASURES_BRFSS)
    for v, r in kg.items():
        assert (r["role"], r["direction"]) == (TIER[v], DIRECTION[v]), v
    ra = {c: (kg[v]["role"], kg[v]["direction"]) for v, c in MEASURES_BRFSS.items()}
    assert not ({c for c, _ in MEASURES_DM.values()} & OUTCOME_CONCEPTS), "R-OUT violated"
    rows = []
    for var, (concept, src) in MEASURES_DM.items():
        if concept in ra:
            role, direction = ra[concept]
            how = "inherited from diabetes RoleAssignment (P7 KG export)"
        else:
            cls = NEW_CONCEPT_CLASS[concept]
            role = RULE[cls]
            direction = "immutable" if role == "immutable" else "unset"
            how = f"new Concept; fixed rule: {cls} -> {role}"
        if role == "immutable" and direction != "immutable":
            how += f"; R-IMM: direction {direction} -> immutable"
            direction = "immutable"
        rows.append({"domain": DOMAIN, "variable": var, "nhanes_source": src, "concept": concept, "role": role,
                     "direction": direction, "derivation": how})
    got = {r["variable"]: (r["role"], r["direction"]) for r in rows}
    diff = {v: (got.get(v), EXPECTED[v]) for v in EXPECTED if got.get(v) != EXPECTED[v]}
    assert not diff, diff
    return rows, sorted(r["variable"] for r in rows if r["role"] == "indicator")


def build(cycle):
    cfg = CYCLES[cycle]
    joined, status = load_cycle(cycle, NHANES_P7_RAW)
    base, prov = build_cycle(joined, cycle)
    j = joined.copy()
    for t, fn in cfg["files"].items():
        d = read_xpt(NHANES_NEW_RAW / cycle / f"{fn}.xpt")
        cols = ["LBXTC"] if t == "TCHOL" else ["KIQ022"]
        j = j.merge(d[["SEQN"] + cols], on="SEQN", how="left", validate="one_to_one")
    df = pd.DataFrame({"SEQN": j["SEQN"].astype("int64")})
    for c in ("HighBP", "BMI", "PhysActivity", "GenHlth", "MentHlth", "Stroke", "HeartDiseaseorAttack", "Age", "Sex",
              "Education", "Income", "AnyHealthcare"):
        df[c] = base[c].values
    df["BMI"] = df["BMI"].round(0)
    tc = pd.to_numeric(j["LBXTC"], errors="coerce")
    df["HighChol"] = np.where(tc.isna(), np.nan, (tc >= 240).astype(float))
    s20, s40 = pd.to_numeric(j["SMQ020"], errors="coerce"), pd.to_numeric(j["SMQ040"], errors="coerce")
    df["Smoker"] = np.select([s20 == 2, (s20 == 1) & s40.isin([1, 2]), (s20 == 1) & (s40 == 3)], [0.0, 1.0, 0.0], np.nan)
    df["KidneyDisease"] = yes_no(j["KIQ022"]).values
    df["Cycle"] = float(cfg["code"])
    sbp = j[SBP].apply(pd.to_numeric, errors="coerce")
    msbp = sbp.mean(axis=1, skipna=True).where(sbp.notna().sum(axis=1) >= 1)
    df["HighBP_measured"] = np.where(msbp.isna(), np.nan, (msbp >= 130).astype(float))
    hb = pd.to_numeric(base["HbA1c"], errors="coerce")
    df["DM_A1C"] = np.where(hb.isna(), np.nan, (hb >= 6.5).astype(float))
    df["DM_DIAG"] = pd.to_numeric(base["Diabetes_self"], errors="coerce").values
    df["HbA1c"] = hb.values
    age = pd.to_numeric(j["RIDAGEYR"], errors="coerce").values
    st = pd.to_numeric(j["RIDSTATR"], errors="coerce").values
    pg = pd.to_numeric(j["RIDEXPRG"], errors="coerce").values
    flow = [("all participants in DEMO", len(df))]
    m = age >= 20
    flow.append(("1 aged 20 years or older", int(m.sum())))
    m &= st == 2
    flow.append(("2 examined at the MEC (RIDSTATR = 2)", int(m.sum())))
    m &= pg != 1
    flow.append(("3 not pregnant (RIDEXPRG != 1)", int(m.sum())))
    m &= (df["DM_A1C"].notna() | df["DM_DIAG"].notna()).values
    flow.append(("4 at least one label available", int(m.sum())))
    hp = {k: prov.get(k) for k in ("HighBP", "PhysActivity", "MentHlth", "GenHlth", "HbA1c", "Diabetes_self")}
    return df[m].copy(), flow, status, hp


def main():
    below_normal()
    check_prereg()
    OUT.mkdir(parents=True, exist_ok=True)
    rows, lock = derive_roles()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    (OUT / "dm_role_table.csv").write_text(buf.getvalue(), encoding="utf-8", newline="\n")
    (OUT / "dm_lock_set.txt").write_text("\n".join(lock) + "\n", encoding="utf-8", newline="\n")
    parts, flows, gate = [], {}, {}
    for cycle in CYCLES:
        d, flow, status, prov = build(cycle)
        parts.append(d)
        flows[cycle] = flow
        gate[cycle] = {"p7_tables_loaded": status, "provenance": prov}
    pooled = pd.concat(parts, ignore_index=True).sort_values(["Cycle", "SEQN"]).reset_index(drop=True)
    f = OUT / "nhanes_dm_rows_2017-2023.csv"
    pooled.to_csv(f, index=False, lineterminator="\n", float_format="%.6f")
    commit = subprocess.run(["git", "-C", str(NHANES_REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    write_json(OUT / "a0_dm.json", {
        "written": datetime.now().isoformat(timespec="seconds"),
        "statement": "Role table and lock set written and hashed before any model of the NHANES diabetes arm (plan S-P5 Section 6).",
        "nhanes_diabetes_commit": commit, "flow": flows, "gate": gate, "rows_csv": str(f), "rows_csv_sha256": sha256_file(f),
        "kg_nodes_sha256": sha256_file(KG_NODES), "role_table_sha256": sha256_file(OUT / "dm_role_table.csv"),
        "lock_set_sha256": sha256_file(OUT / "dm_lock_set.txt"), "lock_set": lock,
        "label_counts": {"DM_A1C_available": int(pooled.DM_A1C.notna().sum()), "DM_A1C_positive": int((pooled.DM_A1C == 1).sum()),
                         "DM_DIAG_available": int(pooled.DM_DIAG.notna().sum()), "DM_DIAG_positive": int((pooled.DM_DIAG == 1).sum())}})
    for r in rows:
        print(r["variable"], r["role"], r["direction"], "|", r["derivation"])
    print("lock", lock, "rows", len(pooled), flows)


if __name__ == "__main__":
    main()
