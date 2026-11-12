"""A0-HTN: derive the hypertension role table and lock set from the KG by script (prereg v3 section 3, steps 1-4,
applied to a third domain as fixed by addendum HTN v1, section 3).

For each Variable of the HTN domain: follow `measures` to its Concept; if the Concept has a RoleAssignment in the
diabetes domain (P7 KG export = depgraph.nodes roles and directions), inherit role and direction; otherwise apply
the fixed rule of prereg v3 section 3 step 3. Two domain rules of the addendum are then applied, both by script:
  R-OUT  the Concept measured by the outcome (BLOOD_PRESSURE) is the domain outcome; it is not a feature and
         has no role in the HTN domain (HighBP is removed from the feature set).
  R-IMM  every feature whose role is immutable has direction immutable, in every generator mode
         (Income, Education and AnyHealthcare are no longer movable upward; review flag of 12/11/2026).
Writes the table and the lock set (all HTN features with role indicator) and their SHA-256, before any HTN model.
Usage: python -I a0_role_table_htn.py [--check]
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I omits the script dir
from htn_common import OUT, P7_REPO, PAPER7, below_normal, check_prereg, sha256_file, write_json  # noqa: E402

sys.path.insert(0, str(P7_REPO / "src"))
from depgraph.nodes import DIRECTION, TIER  # noqa: E402

KG_NODES = PAPER7 / "outputs" / "kg_export" / "dependency_graph_nodes.csv"
DEST = OUT / "a0_role_table"
DOMAIN = "Hypertension (MONDO:0005044)"
OUTCOME_CONCEPT = "BLOOD_PRESSURE"

MEASURES_BRFSS = {  # identical to q1_domain_ckd/a0_role_table.py
    "HighBP": "BLOOD_PRESSURE", "HighChol": "CHOLESTEROL", "BMI": "BODY_WEIGHT", "Smoker": "SMOKING",
    "PhysActivity": "PHYSICAL_ACTIVITY", "Fruits": "FRUIT_INTAKE", "Veggies": "VEGETABLE_INTAKE",
    "HvyAlcoholConsump": "ALCOHOL", "NoDocbcCost": "COST_BARRIER", "GenHlth": "GENERAL_HEALTH",
    "MentHlth": "MENTAL_HEALTH", "PhysHlth": "PHYSICAL_FUNCTION", "DiffWalk": "MOBILITY", "Age": "AGE", "Sex": "SEX",
    "Stroke": "STROKE_HISTORY", "HeartDiseaseorAttack": "CHD_MI_HISTORY", "Income": "INCOME", "Education": "EDUCATION",
    "AnyHealthcare": "HEALTH_COVERAGE", "CholCheck": "CHOLESTEROL_CHECK",
}
# measures: HTN domain (pooled NHANES Variables, addendum section 4) -> Concept, with the NHANES source
MEASURES_HTN = {
    "Diabetes": ("DIABETES_HISTORY", "DIQ010 = 1"),
    "HighChol": ("CHOLESTEROL", "LBXTC >= 240 mg/dL (measured)"),
    "BMI": ("BODY_WEIGHT", "BMXBMI, integer"),
    "Smoker": ("SMOKING", "SMQ020 = 1 and SMQ040 in {1, 2} (current)"),
    "PhysActivity": ("PHYSICAL_ACTIVITY", "2017-2020 PAQ605; 2021-2023 PAD790Q/U-PAD820 (gpaq_v2, moderate + 2 x vigorous >= 150 min/week)"),
    "GenHlth": ("GENERAL_HEALTH", "HUQ010"),
    "MentHlth": ("MENTAL_HEALTH", "PHQ-9 total in P7 bands"),
    "Stroke": ("STROKE_HISTORY", "MCQ160F"),
    "HeartDiseaseorAttack": ("CHD_MI_HISTORY", "MCQ160C or MCQ160E"),
    "KidneyDisease": ("KIDNEY_DISEASE_HISTORY", "KIQ022 = 1 (ever told weak or failing kidneys)"),
    "Age": ("AGE", "RIDAGEYR"), "Sex": ("SEX", "RIAGENDR"), "Education": ("EDUCATION", "DMDEDUC2"),
    "Income": ("INCOME", "INDFMPIR, 5 bands"), "AnyHealthcare": ("HEALTH_COVERAGE", "HIQ011"),
    "Cycle": ("SURVEY_CYCLE", "0 = 2017-2020, 1 = 2021-2023"),
}
OUTCOME_VARIABLES = {"HTN_L1_measured": "mean BPXOSY1-3 >= 130 or mean BPXODI1-3 >= 80 mmHg (>= 2 readings each)",
                     "HTN_L2_measured_or_treated": "L1 or BPQ050A / BPQ150 = 1 (now taking prescribed BP medicine)"}
RULE = {"diagnosis_history": "immutable", "demographic": "immutable", "survey_design": "immutable",
        "behaviour": "lever", "measured_clinical_risk_factor": "treatable", "patient_reported_health_status": "indicator"}
NEW_CONCEPT_CLASS = {"DIABETES_HISTORY": "diagnosis_history", "KIDNEY_DISEASE_HISTORY": "diagnosis_history",
                     "SURVEY_CYCLE": "survey_design"}
# addendum section 3 table, used only as an assertion after derivation
EXPECTED = {"Diabetes": ("immutable", "immutable"), "HighChol": ("treatable", "monotonic_down"),
            "BMI": ("lever", "bidirectional"), "Smoker": ("lever", "monotonic_down"),
            "PhysActivity": ("lever", "monotonic_up"), "GenHlth": ("indicator", "monotonic_down"),
            "MentHlth": ("indicator", "monotonic_down"), "Stroke": ("immutable", "immutable"),
            "HeartDiseaseorAttack": ("immutable", "immutable"), "KidneyDisease": ("immutable", "immutable"),
            "Age": ("immutable", "immutable"), "Sex": ("immutable", "immutable"), "Education": ("immutable", "immutable"),
            "Income": ("immutable", "immutable"), "AnyHealthcare": ("immutable", "immutable"),
            "Cycle": ("immutable", "immutable")}


def derive():
    kg = {r["node"]: r for r in csv.DictReader(open(KG_NODES, encoding="utf-8"))}
    assert set(kg) == set(TIER) == set(MEASURES_BRFSS)
    for v, r in kg.items():
        assert (r["role"], r["direction"]) == (TIER[v], DIRECTION[v]), v
    ra_diab = {}
    for v, c in MEASURES_BRFSS.items():
        ra = (kg[v]["role"], kg[v]["direction"])
        assert c not in ra_diab or ra_diab[c] == ra, f"conflicting diabetes roles for {c}"
        ra_diab[c] = ra
    assert OUTCOME_CONCEPT not in {c for c, _ in MEASURES_HTN.values()}, "R-OUT: outcome Concept used as a feature"
    rows = []
    for var, (concept, src) in MEASURES_HTN.items():
        if concept in ra_diab:
            role, direction = ra_diab[concept]
            how = "inherited from diabetes RoleAssignment (P7 KG export)"
        else:
            cls = NEW_CONCEPT_CLASS[concept]
            role = RULE[cls]
            direction = "immutable" if role == "immutable" else "unset"
            how = f"new Concept; fixed rule: {cls} -> {role}"
        if role == "immutable" and direction != "immutable":
            how += f"; R-IMM: direction {direction} -> immutable"
            direction = "immutable"
        rows.append({"domain": DOMAIN, "variable": var, "nhanes_source": src, "concept": concept,
                     "role": role, "direction": direction, "derivation": how})
    got = {r["variable"]: (r["role"], r["direction"]) for r in rows}
    diff = {v: (got.get(v), EXPECTED[v]) for v in EXPECTED if got.get(v) != EXPECTED[v]}
    assert not diff, f"derived table differs from the addendum table: {diff}"
    lock = sorted(r["variable"] for r in rows if r["role"] == "indicator")
    movable = [v for v, (r, d) in got.items() if d not in ("immutable", "conditional")]
    return rows, lock, movable


def table_text(rows) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main():
    below_normal()
    check_prereg()
    rows, lock, movable = derive()
    tab, lock_txt = table_text(rows), "\n".join(lock) + "\n"
    if "--check" in sys.argv:
        rec = json.loads((DEST / "htn_role_table_hash.json").read_text(encoding="utf-8"))
        h_tab = hashlib.sha256(tab.encode("utf-8")).hexdigest()
        h_lock = hashlib.sha256(lock_txt.encode("utf-8")).hexdigest()
        same = h_tab == rec["htn_role_table_sha256"] and h_lock == rec["htn_lock_set_sha256"]
        print("role table re-derived:", h_tab, "lock:", h_lock, "UNCHANGED" if same else "CHANGED")
        sys.exit(0 if same else 1)
    DEST.mkdir(parents=True, exist_ok=True)
    path, lock_path = DEST / "htn_role_table.csv", DEST / "htn_lock_set.txt"
    path.write_text(tab, encoding="utf-8", newline="\n")
    lock_path.write_text(lock_txt, encoding="utf-8", newline="\n")
    write_json(DEST / "htn_role_table_hash.json", {
        "written": datetime.now().isoformat(timespec="seconds"),
        "statement": "Generated and hashed before any HTN model was fitted (prereg v3 section 3 step 4; addendum HTN v1 section 3).",
        "kg_nodes_sha256": sha256_file(KG_NODES), "htn_role_table_sha256": sha256_file(path),
        "htn_lock_set_sha256": sha256_file(lock_path), "lock_set": lock,
        "outcome_concept_R_OUT": OUTCOME_CONCEPT, "outcome_variables": OUTCOME_VARIABLES,
        "movable_for_null_O_A2": movable})
    for r in rows:
        print(r["variable"], r["concept"], r["role"], r["direction"], "|", r["derivation"])
    print("lock set", lock, "movable", movable)


if __name__ == "__main__":
    main()
