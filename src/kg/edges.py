"""Dependency edges of the clinical knowledge graph K_G.

Every edge is asserted from a numbered recommendation in the ADA Standards of
Care in Diabetes - 2026 (Diabetes Care 2026;49 Suppl. 1) and carries the
evidence grade the ADA Professional Practice Committee assigned to it:

    A  clear evidence from well-conducted, generalizable RCTs, or meta-analyses
    B  RCTs with an identified flaw, or well-conducted cohort / case-control studies
    C  poorly controlled or uncontrolled studies, case series, or conflicting evidence
    E  expert consensus or clinical experience
    -  narrative statement in the section text rather than a numbered recommendation

No edge is inferred from correlations in BRFSS. Deriving the constraint from the
same data the counterfactual generator exploits would be circular.

Only the citation string and the grade are stored. ADA guideline text is not
reproduced here: the Standards of Care may not be redistributed or text-mined
without permission.

Sections used:
    S5   Facilitating Positive Health Behaviors and Well-being to Improve
         Health Outcomes.                 doi:10.2337/dc26-S005, S89-S131
    S8   Obesity and Weight Management.   doi:10.2337/dc26-S008
         (reviewed and approved by The Obesity Society)
    S10  Cardiovascular Disease and Risk Management.
                                          doi:10.2337/dc26-S010, S216-S245
         (reviewed and approved by the American College of Cardiology)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Edge:
    src: str          # the lever acted upon
    dst: str          # the feature it is a recognised route to changing
    grade: str        # ADA evidence grade: A, B, C, E, or "-" for narrative
    source: str       # section and recommendation number
    gloss: str        # one-line paraphrase; NOT ADA text


EDGES: List[Edge] = [
    # ---------------------------------------------------------------- levers -> BMI
    Edge("PhysActivity", "BMI", "A", "SoC 2026, S5, Rec 5.12",
         "A weight-management plan built on nutrition, physical activity and "
         "behavioural support targets 5-7% weight loss."),
    Edge("PhysActivity", "BMI", "A", "SoC 2026, S8, Rec 8.8a",
         "Structured counselling centred on nutrition and physical activity to "
         "achieve a daily energy deficit."),
    Edge("Fruits", "BMI", "B", "SoC 2026, S5, Rec 5.14",
         "Eating patterns should emphasise whole fruits, among other principles."),
    Edge("Veggies", "BMI", "B", "SoC 2026, S5, Rec 5.14",
         "Eating patterns should emphasise nonstarchy vegetables, among other principles."),
    Edge("Fruits", "BMI", "A", "SoC 2026, S5, Rec 5.12",
         "Nutrition is one of the three components of the weight-management plan."),
    Edge("Veggies", "BMI", "A", "SoC 2026, S5, Rec 5.12",
         "Nutrition is one of the three components of the weight-management plan."),

    # ------------------------------------------------------- BMI -> comorbidities
    Edge("BMI", "HighBP", "A", "SoC 2026, S8, Rec 8.5",
         "Weight loss of 5-7% improves glycaemia and intermediate cardiovascular "
         "risk factors."),
    Edge("BMI", "HighChol", "A", "SoC 2026, S8, Rec 8.5",
         "Same recommendation; dyslipidaemia is among the intermediate "
         "cardiovascular risk factors."),
    Edge("BMI", "HighBP", "A", "SoC 2026, S10, Rec 10.5",
         "Weight loss is the first lifestyle behaviour advised above 120/80 mmHg."),

    # --------------------------------------------- lifestyle levers -> HighBP
    # Rec 10.5 (grade A) names five lifestyle behaviours in a single sentence.
    # It is the single most load-bearing recommendation in this graph.
    Edge("PhysActivity", "HighBP", "A", "SoC 2026, S10, Rec 10.5",
         "Increased physical activity is one of the advised lifestyle behaviours."),
    Edge("Fruits", "HighBP", "A", "SoC 2026, S10, Rec 10.5",
         "A DASH-style eating pattern is one of the advised lifestyle behaviours."),
    Edge("Veggies", "HighBP", "A", "SoC 2026, S10, Rec 10.5",
         "A DASH-style eating pattern is one of the advised lifestyle behaviours."),
    Edge("HvyAlcoholConsump", "HighBP", "A", "SoC 2026, S10, Rec 10.5",
         "Limiting or avoiding alcohol is one of the advised lifestyle behaviours."),
    Edge("Smoker", "HighBP", "A", "SoC 2026, S10, Rec 10.5",
         "Smoking cessation is one of the advised lifestyle behaviours."),
    Edge("HvyAlcoholConsump", "HighBP", "B", "SoC 2026, S5, Rec 5.18",
         "Adults with or at risk of diabetes should not exceed recommended daily "
         "alcohol limits."),

    # ------------------------------------------- lifestyle levers -> HighChol
    Edge("PhysActivity", "HighChol", "C", "SoC 2026, S10, Rec 10.15",
         "Lifestyle therapy is intensified for raised triglycerides or low HDL."),
    Edge("Fruits", "HighChol", "C", "SoC 2026, S10, Rec 10.15",
         "Lifestyle therapy is intensified for raised triglycerides or low HDL."),
    Edge("Veggies", "HighChol", "C", "SoC 2026, S10, Rec 10.15",
         "Lifestyle therapy is intensified for raised triglycerides or low HDL."),

    # ------------------------------------------------ levers -> indicators
    # These are the edges that make the audit rule bite: they are the ONLY
    # guideline-recognised routes to changing a health-status indicator.
    Edge("PhysActivity", "PhysHlth", "-", "SoC 2026, S5, physical activity narrative",
         "Physical activity is described as favourably affecting mobility and "
         "physical function."),
    Edge("PhysActivity", "MentHlth", "-", "SoC 2026, S5, physical activity narrative",
         "Physical activity is described as favourably affecting psychosocial "
         "well-being, and as benefiting depressive symptoms."),
    Edge("PhysActivity", "GenHlth", "-", "SoC 2026, S5, physical activity narrative",
         "Physical activity is described as favourably affecting glycaemia, "
         "cardiovascular risk factors, weight, body composition and physical function."),
    Edge("Smoker", "PhysHlth", "-", "SoC 2026, S5, tobacco narrative",
         "Smoking is described as causally linked to multiple health risks that "
         "affect morbidity in people with diabetes."),
    Edge("BMI", "GenHlth", "-", "SoC 2026, S8, obesity narrative",
         "Obesity treatment is framed as improving health outcomes broadly."),
    Edge("BMI", "PhysHlth", "-", "SoC 2026, S8, obesity narrative",
         "Obesity treatment is framed as improving health outcomes broadly."),
    Edge("HighBP", "GenHlth", "-", "SoC 2026, S10, narrative",
         "Blood-pressure control is framed as reducing cardiovascular risk and "
         "improving outcomes."),
    Edge("HighChol", "GenHlth", "-", "SoC 2026, S10, narrative",
         "Lipid control is framed as reducing cardiovascular risk and improving "
         "outcomes."),
]


# ---------------------------------------------------------------------------
# The decisive negative result.
#
# ADA Standards of Care 2026, sections 5, 8 and 10 were searched for any
# recommendation whose INTERVENTION TARGET is self-rated general health,
# physically-unhealthy days, or mentally-unhealthy days.
#
# There is none.
#
# These constructs appear only as things to be ASSESSED, as goals:
#   S5, Rec 5.3 [C] - assess clinical outcomes, health status and well-being as
#                     key goals of diabetes self-management education and support.
# and the section is titled "Facilitating Positive Health BEHAVIORS ... TO
# IMPROVE Health OUTCOMES", which is the same distinction this paper draws.
#
# The absence is not a gap in our search. It is the guideline-level justification
# for the indicator tier: a clinician is never told to intervene ON self-rated
# health, only to move it BY acting on behaviours.
# ---------------------------------------------------------------------------
NO_GUIDELINE_TARGETS_INDICATORS = ("GenHlth", "PhysHlth", "MentHlth")


def in_neighbours(node: str, levers_only: bool = True) -> set[str]:
    """Features that the guidelines recognise as routes to changing `node`."""
    from kg.nodes import TIER  # local import to keep this module standalone-readable
    srcs = {e.src for e in EDGES if e.dst == node}
    if levers_only:
        srcs = {s for s in srcs if TIER.get(s) == "lever"}
    return srcs


def by_grade(grade: str) -> List[Edge]:
    return [e for e in EDGES if e.grade == grade]


if __name__ == "__main__":
    from collections import Counter
    c = Counter(e.grade for e in EDGES)
    print(f"{len(EDGES)} edges")
    for g in ("A", "B", "C", "E", "-"):
        if c[g]:
            print(f"  grade {g}: {c[g]}")
    print("\nDistinct (src, dst) pairs:", len({(e.src, e.dst) for e in EDGES}))
