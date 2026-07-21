"""Nodes of the dependency graph K_G.

The published knowledge layer K(f) carries one axis per feature: the DIRECTION in
which a counterfactual may move it. This module adds the second axis the flat
table cannot express: the feature's ROLE.

    lever      the patient can act on it directly
    treatable  it can be changed, but through a clinician
    indicator  it REPORTS health status; it is not something a patient does
    immutable  it cannot be changed, or is a selection-effect proxy rather than
               a causal pathway

The direction axis is reproduced from the audited system unchanged, so that any
difference in behaviour is attributable to the role axis alone.
"""
from __future__ import annotations

from typing import Dict

# Direction classes, verbatim from the audited system's taxonomy.
DIRECTION: Dict[str, str] = {
    "Age": "immutable", "Sex": "immutable",
    "Stroke": "immutable", "HeartDiseaseorAttack": "immutable",
    "PhysActivity": "monotonic_up", "Fruits": "monotonic_up",
    "Veggies": "monotonic_up", "AnyHealthcare": "monotonic_up",
    "CholCheck": "monotonic_up", "Education": "monotonic_up",
    "Income": "monotonic_up",
    "Smoker": "monotonic_down", "HvyAlcoholConsump": "monotonic_down",
    "NoDocbcCost": "monotonic_down", "HighBP": "monotonic_down",
    "HighChol": "monotonic_down", "GenHlth": "monotonic_down",
    "MentHlth": "monotonic_down", "PhysHlth": "monotonic_down",
    "BMI": "bidirectional",
    "DiffWalk": "conditional",
}

# The axis this paper adds.
TIER: Dict[str, str] = {
    # ---- levers: the patient acts on these directly -------------------------
    "BMI": "lever",
    "PhysActivity": "lever",
    "Fruits": "lever",
    "Veggies": "lever",
    "Smoker": "lever",
    "HvyAlcoholConsump": "lever",
    "NoDocbcCost": "lever",

    # ---- treatable: real targets, but reached through a clinician -----------
    "HighBP": "treatable",
    "HighChol": "treatable",

    # ---- indicators: these REPORT status, they are not actions --------------
    # No ADA recommendation in Standards of Care 2026 sections 5, 8 or 10 takes
    # any of these as an intervention target. They appear only as goals to be
    # assessed (S5, Rec 5.3). See depgraph/edges.py.
    "GenHlth": "indicator",
    "PhysHlth": "indicator",
    "MentHlth": "indicator",
    "DiffWalk": "indicator",

    # ---- immutable, or selection-effect proxies ----------------------------
    "Age": "immutable", "Sex": "immutable",
    "Stroke": "immutable", "HeartDiseaseorAttack": "immutable",
    "Income": "immutable", "Education": "immutable",
    "AnyHealthcare": "immutable", "CholCheck": "immutable",
}

LEVERS = {f for f, t in TIER.items() if t == "lever"}
TREATABLE = {f for f, t in TIER.items() if t == "treatable"}
INDICATORS = {f for f, t in TIER.items() if t == "indicator"}
IMMUTABLE = {f for f, t in TIER.items() if t == "immutable"}

# ---------------------------------------------------------------------------
# A boundary that is a judgment, not a measurement.
#
# HighBP and HighChol are placed in `treatable` because pharmacotherapy and
# clinician-directed lifestyle therapy are recognised routes to changing them
# (SoC 2026, S10). A reviewer may reasonably argue they are also downstream of
# BMI and therefore indicators. The paper reports the audit under BOTH readings.
# Announcing that the boundary is a judgment is what keeps the analysis honest.
# ---------------------------------------------------------------------------
STRICT_INDICATORS = INDICATORS | TREATABLE

assert set(TIER) == set(DIRECTION), "node sets must agree"
assert len(TIER) == 21, "BRFSS 2021 has 21 features"
