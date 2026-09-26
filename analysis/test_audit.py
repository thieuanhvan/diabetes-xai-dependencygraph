"""Hand-checked regression test for depgraph.audit.

Standalone: `python analysis/test_audit.py`
No data, no model, no pipeline repo required. Run this after any change to
src/depgraph/edges.py or src/depgraph/nodes.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from depgraph.audit import classify, lever_in_neighbours, summarise  # noqa: E402


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print(f"  ok  {msg}")


print("lever in-neighbourhoods of the indicator tier")
check(lever_in_neighbours("GenHlth") == {"BMI", "PhysActivity"}, "GenHlth <- BMI, PhysActivity")
check(lever_in_neighbours("PhysHlth") == {"BMI", "PhysActivity", "Smoker"}, "PhysHlth <- BMI, PhysActivity, Smoker")
check(lever_in_neighbours("MentHlth") == {"PhysActivity"}, "MentHlth <- PhysActivity")
check(lever_in_neighbours("DiffWalk") == set(), "DiffWalk has no lever route")
check(lever_in_neighbours("GenHlth", "ABC") == set(),
      "no GRADED lever edge reaches GenHlth: the audit rests on narrative edges")

print("\nsingle counterfactuals")
check(classify(["PhysActivity", "MentHlth"])["unsupported"] is False,
      "PhysActivity -> MentHlth is a guideline route, so supported")
check(classify(["BMI", "MentHlth"])["unsupported"] is True,
      "BMI -> MentHlth has no edge, so unsupported under the edge rule")
check(classify(["BMI", "MentHlth"], rule="role")["unsupported"] is False,
      "the same case is SUPPORTED under the role-only rule: this is the gap")
check(classify(["GenHlth", "Income"])["fully_unactionable"] is True,
      "indicator plus SES proxy only is fully unactionable")
check(classify(["GenHlth", "BMI"])["fully_unactionable"] is False,
      "a lever makes it not fully unactionable")
check(classify(["HighBP", "BMI"], reading="narrow")["touches_target"] is False,
      "treatables are not targets under the narrow reading")
check(classify(["HighBP", "BMI"], reading="broad")["unsupported"] is False,
      "BMI -> HighBP is grade A, so supported under the broad reading")
check(classify(["HighBP", "Income"], reading="broad")["unsupported"] is True,
      "Income is not a lever, so HighBP is unsupported")
check(classify([])["touches_target"] is False, "a counterfactual with no changes touches nothing")

print("\naggregate over a hand-built set")
per_cf = [["BMI", "MentHlth"], ["PhysActivity", "MentHlth"], ["GenHlth", "Smoker"],
          ["GenHlth", "BMI"], ["GenHlth", "Income"], ["Income", "Education"],
          ["HighBP", "BMI"], ["HighBP", "Income"], []]
n = summarise(per_cf, reading="narrow", rule="role")
e = summarise(per_cf, reading="narrow", rule="edge")
b = summarise(per_cf, reading="broad", rule="edge")
check(n["cf_touching_target"] == 5, "5 of 9 touch an indicator")
check(n["cf_unsupported"] == 1, "role rule flags 1")
check(e["cf_unsupported"] == 3, "edge rule flags 3")
check(b["cf_touching_target"] == 7, "7 of 9 touch an indicator or a treatable")
check(b["cf_unsupported"] == 4, "broad edge rule flags 4")
check(n["cf_fully_unactionable"] == 1, "1 fully unactionable")

print("\nALL CHECKS PASSED")


def test_audit_regression_suite():
    """Lets `python -m pytest` collect this file.

    The checks above run at import time; any failing check raises during
    collection, which pytest reports as an error. Reaching this function
    means every check passed.
    """
    assert True
