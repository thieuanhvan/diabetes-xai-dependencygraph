"""A0: derive the CKD role table and lock set from the KG by script (prereg v3 section 3, steps 1-4).

For each Variable of the CKD domain: follow `measures` to its Concept; if the Concept has a RoleAssignment in
the diabetes domain (the P7 KG export, roles and directions of depgraph.nodes), inherit role and direction;
otherwise apply the fixed rule (diagnosis-history, demographic or survey-design item -> immutable; behaviour ->
lever; measured clinical risk factor reached through care -> treatable; patient-reported health status ->
indicator). Writes the table and the lock set (all CKD Concepts with role indicator) and their SHA-256,
before any CKD model is fitted. Usage: python -I a0_role_table.py
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime

from q1_common import OUT, P7_REPO, PAPER7, below_normal, check_prereg, sha256_file, write_json

sys.path.insert(0, str(P7_REPO / "src"))
from depgraph.nodes import DIRECTION, TIER  # noqa: E402

KG_NODES = PAPER7 / "outputs" / "kg_export" / "dependency_graph_nodes.csv"
DEST = OUT / "a0_role_table"

# measures: diabetes domain (BRFSS 2021 Variables of P7) -> Concept
MEASURES_BRFSS = {
    "HighBP": "BLOOD_PRESSURE", "HighChol": "CHOLESTEROL", "BMI": "BODY_WEIGHT", "Smoker": "SMOKING",
    "PhysActivity": "PHYSICAL_ACTIVITY", "Fruits": "FRUIT_INTAKE", "Veggies": "VEGETABLE_INTAKE",
    "HvyAlcoholConsump": "ALCOHOL", "NoDocbcCost": "COST_BARRIER", "GenHlth": "GENERAL_HEALTH",
    "MentHlth": "MENTAL_HEALTH", "PhysHlth": "PHYSICAL_FUNCTION", "DiffWalk": "MOBILITY", "Age": "AGE", "Sex": "SEX",
    "Stroke": "STROKE_HISTORY", "HeartDiseaseorAttack": "CHD_MI_HISTORY", "Income": "INCOME", "Education": "EDUCATION",
    "AnyHealthcare": "HEALTH_COVERAGE", "CholCheck": "CHOLESTEROL_CHECK",
}
# measures: CKD domain (pooled NHANES Variables, prereg 4.5) -> Concept, with the NHANES source
MEASURES_CKD = {
    "Diabetes": ("DIABETES_HISTORY", "DIQ010 = 1"),
    "HighBP": ("BLOOD_PRESSURE", "mean BPXOSY1-3 >= 130 mmHg (measured)"),
    "HighChol": ("CHOLESTEROL", "LBXTC >= 240 mg/dL (measured)"),
    "BMI": ("BODY_WEIGHT", "BMXBMI, integer"),
    "Smoker": ("SMOKING", "SMQ020 = 1 and SMQ040 in {1, 2} (current)"),
    "PhysActivity": ("PHYSICAL_ACTIVITY", "2017-2020 PAQ605; 2021-2023 PAD800/PAD820 (as P7)"),
    "GenHlth": ("GENERAL_HEALTH", "HUQ010"),
    "MentHlth": ("MENTAL_HEALTH", "PHQ-9 total in P7 bands"),
    "Stroke": ("STROKE_HISTORY", "MCQ160F"),
    "HeartDiseaseorAttack": ("CHD_MI_HISTORY", "MCQ160C or MCQ160E"),
    "Age": ("AGE", "RIDAGEYR"), "Sex": ("SEX", "RIAGENDR"), "Education": ("EDUCATION", "DMDEDUC2"),
    "Income": ("INCOME", "INDFMPIR, 5 bands"), "AnyHealthcare": ("HEALTH_COVERAGE", "HIQ011"),
    "Cycle": ("SURVEY_CYCLE", "0 = 2017-2020, 1 = 2021-2023"),
}
# fixed rule for Concepts without a diabetes RoleAssignment (prereg 3, step 3): concept class -> role
RULE = {"diagnosis_history": "immutable", "demographic": "immutable", "survey_design": "immutable",
        "behaviour": "lever", "measured_clinical_risk_factor": "treatable", "patient_reported_health_status": "indicator"}
NEW_CONCEPT_CLASS = {"DIABETES_HISTORY": "diagnosis_history", "SURVEY_CYCLE": "survey_design"}
# prereg 4.5 table, used only as an assertion after derivation
EXPECTED = {"Diabetes": ("immutable", "immutable"), "HighBP": ("treatable", "monotonic_down"),
            "HighChol": ("treatable", "monotonic_down"), "BMI": ("lever", "bidirectional"),
            "Smoker": ("lever", "monotonic_down"), "PhysActivity": ("lever", "monotonic_up"),
            "GenHlth": ("indicator", "monotonic_down"), "MentHlth": ("indicator", "monotonic_down"),
            "Stroke": ("immutable", "immutable"), "HeartDiseaseorAttack": ("immutable", "immutable"),
            "Age": ("immutable", "immutable"), "Sex": ("immutable", "immutable"), "Education": ("immutable", "monotonic_up"),
            "Income": ("immutable", "monotonic_up"), "AnyHealthcare": ("immutable", "monotonic_up"),
            "Cycle": ("immutable", "immutable")}


def main():
    below_normal()
    check_prereg()
    DEST.mkdir(parents=True, exist_ok=True)
    kg = {r["node"]: r for r in csv.DictReader(open(KG_NODES, encoding="utf-8"))}
    assert set(kg) == set(TIER) == set(MEASURES_BRFSS)
    for v, r in kg.items():  # the KG export must carry exactly the depgraph roles and directions
        assert (r["role"], r["direction"]) == (TIER[v], DIRECTION[v]), v
    # RoleAssignment(concept, diabetes)
    ra_diab = {}
    for v, c in MEASURES_BRFSS.items():
        ra = (kg[v]["role"], kg[v]["direction"])
        assert c not in ra_diab or ra_diab[c] == ra, f"conflicting diabetes roles for {c}"
        ra_diab[c] = ra
    rows = []
    for var, (concept, src) in MEASURES_CKD.items():
        if concept in ra_diab:
            role, direction = ra_diab[concept]
            how = "inherited from diabetes RoleAssignment (P7 KG export)"
        else:
            cls = NEW_CONCEPT_CLASS[concept]
            role = RULE[cls]
            direction = "immutable" if role == "immutable" else "unset"
            how = f"new Concept; fixed rule: {cls} -> {role}"
        rows.append({"domain": "CKD (MONDO:0005300)", "variable": var, "nhanes_source": src, "concept": concept,
                     "role": role, "direction": direction, "derivation": how})
    got = {r["variable"]: (r["role"], r["direction"]) for r in rows}
    diff = {v: (got[v], EXPECTED[v]) for v in EXPECTED if got.get(v) != EXPECTED[v]}
    assert not diff, f"derived table differs from prereg 4.5: {diff}"
    lock = sorted(r["variable"] for r in rows if r["role"] == "indicator")
    if "--check" in sys.argv:  # re-derive and compare with the hashed files, write nothing
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        import hashlib
        h_tab = hashlib.sha256(buf.getvalue().encode("utf-8")).hexdigest()
        h_lock = hashlib.sha256(("\n".join(lock) + "\n").encode("utf-8")).hexdigest()
        rec = __import__("json").loads((DEST / "ckd_role_table_hash.json").read_text(encoding="utf-8"))
        same = h_tab == rec["ckd_role_table_sha256"] and h_lock == rec["ckd_lock_set_sha256"]
        print("role table re-derived:", h_tab, "lock:", h_lock, "UNCHANGED" if same else "CHANGED")
        sys.exit(0 if same else 1)
    path = DEST / "ckd_role_table.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    lock_path = DEST / "ckd_lock_set.txt"
    lock_path.write_text("\n".join(lock) + "\n", encoding="utf-8", newline="\n")
    write_json(DEST / "ckd_role_table_hash.json", {
        "written": datetime.now().isoformat(timespec="seconds"),
        "statement": "Generated and hashed before any CKD model was fitted (prereg v3 section 3, step 4).",
        "kg_nodes_sha256": sha256_file(KG_NODES), "ckd_role_table_sha256": sha256_file(path),
        "ckd_lock_set_sha256": sha256_file(lock_path), "lock_set": lock,
        "movable_for_null_O_A2": [v for v, (r, d) in got.items() if d not in ("immutable", "conditional")]})
    for r in rows:
        print(r["variable"], r["concept"], r["role"], r["direction"], "|", r["derivation"])
    print("lock set", lock)


if __name__ == "__main__":
    main()
