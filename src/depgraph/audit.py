"""The audit rule of Section IV-E, as a single testable function.

WHY THIS MODULE EXISTS
----------------------
The rule was previously inlined in ``run_seed_sweep.py`` as::

    if ind and not lev:          # indicator changed, and NO lever changed
        n_unsup += 1

which is a *role-only* rule: it never consults the edge set ``E``. The rule the
paper states in Section IV-E is stronger, and edge-aware:

    a change to v is unsupported when
        tier(v) = indicator  AND  { u : (u->v) in E, tier(u) = lever, u in S } = empty

The two disagree whenever a counterfactual moves an indicator while pulling a
lever that has no guideline-recognised route to *that* indicator (for example
lowering BMI to move MentHlth: the ADA narrative supports PhysActivity ->
MentHlth, not BMI -> MentHlth).

Both rules are implemented here so the difference can be reported rather than
hidden. ``rule="role"`` reproduces the previous behaviour bit for bit.

TERMS
-----
reading   which tiers count as audit targets
            "narrow"  indicators only                      (paper's main reading)
            "broad"   indicators and treatables            (paper's Section V-E)
rule      "edge"  Section IV-E, requires a lever with an edge into that target
          "role"  requires any lever at all, ignores E
grades    restrict which edges may confer support, e.g. {"A","B","C"} to see
          what the graded edges alone can carry. None means all edges.
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional, Set

from depgraph.edges import EDGES
from depgraph.nodes import INDICATORS, LEVERS, TIER, TREATABLE

READINGS = ("narrow", "broad")
RULES = ("edge", "role")


def _tier_members(tier: str) -> Set[str]:
    """Derived from TIER, so a caller that overrides TIER changes the target set
    as well as the lever set. Reading the module-level INDICATORS list instead
    would make a tier reassignment a silent no-op."""
    return {f for f, t in TIER.items() if t == tier}


def targets_of(reading: str) -> Set[str]:
    if reading == "narrow":
        return _tier_members("indicator")
    if reading == "broad":
        return _tier_members("indicator") | _tier_members("treatable")
    raise ValueError(f"reading must be one of {READINGS}, got {reading!r}")


def lever_in_neighbours(target: str, grades: Optional[Iterable[str]] = None) -> Set[str]:
    """Levers the guidelines recognise as a route to changing `target`."""
    g = None if grades is None else set(grades)
    return {e.src for e in EDGES
            if e.dst == target and TIER.get(e.src) == "lever"
            and (g is None or e.grade in g)}


def is_supported(target: str, changed: Set[str], *, rule: str = "edge",
                 grades: Optional[Iterable[str]] = None) -> bool:
    """Does this counterfactual pull a lever that licenses moving `target`?"""
    if rule == "edge":
        return bool(lever_in_neighbours(target, grades) & changed)
    if rule == "role":
        return any(TIER.get(f) == "lever" for f in changed)
    raise ValueError(f"rule must be one of {RULES}, got {rule!r}")


def classify(changed: Iterable[str], *, reading: str = "narrow", rule: str = "edge",
             grades: Optional[Iterable[str]] = None) -> Dict:
    """Classify one counterfactual, given the set of features it changes.

    Returns
        targets_touched      audit targets this counterfactual moves
        unsupported_targets  those with no guideline route from a pulled lever
        touches_target       bool
        unsupported          bool, true if ANY touched target is unsupported
        n_unsupported_changes    how many individual changes are unsupported
        fully_unactionable   nothing a patient can act on: no lever, no treatable,
                             and at least one indicator moved. Independent of
                             `rule` and `reading`; this is the 11.1% headline.
    """
    S = set(changed)
    tgts = sorted(S & targets_of(reading))
    unsup = [v for v in tgts if not is_supported(v, S, rule=rule, grades=grades)]
    has_lever = any(TIER.get(f) == "lever" for f in S)
    has_treatable = any(TIER.get(f) == "treatable" for f in S)
    moves_indicator = any(TIER.get(f) == "indicator" for f in S)
    return {
        "targets_touched": tgts,
        "unsupported_targets": unsup,
        "touches_target": bool(tgts),
        "unsupported": bool(unsup),
        "n_unsupported_changes": len(unsup),
        "fully_unactionable": bool(moves_indicator and not has_lever and not has_treatable),
    }


def summarise(cf_changes: Iterable[Iterable[str]], *, reading: str = "narrow",
              rule: str = "edge", grades: Optional[Iterable[str]] = None) -> Dict:
    """Aggregate `classify` over a collection of counterfactuals."""
    n_cf = n_touch = n_unsup = n_unsup_chg = n_pure = 0
    for changed in cf_changes:
        n_cf += 1
        r = classify(changed, reading=reading, rule=rule, grades=grades)
        n_touch += r["touches_target"]
        n_unsup += r["unsupported"]
        n_unsup_chg += r["n_unsupported_changes"]
        n_pure += r["fully_unactionable"]
    return {
        "reading": reading, "rule": rule,
        "grades": "all" if grades is None else "".join(sorted(grades)),
        "n_cf": n_cf,
        "cf_touching_target": n_touch,
        "cf_unsupported": n_unsup,
        "unsupported_changes": n_unsup_chg,
        "cf_fully_unactionable": n_pure,
    }


if __name__ == "__main__":
    for v in sorted(INDICATORS):
        print(f"{v:10s} lever in-neighbours: {sorted(lever_in_neighbours(v)) or 'none'}"
              f"   graded only (A/B/C): {sorted(lever_in_neighbours(v, 'ABC')) or 'none'}")
