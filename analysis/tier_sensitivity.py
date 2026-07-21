"""How much does the audit depend on the contested tier assignments?

Standalone: `python analysis/tier_sensitivity.py`

The lever/treatable/indicator boundary is a judgment, and the paper says so. This
turns that admission into a measurement: reassign one contested feature at a
time and report how the unsupported count moves.

Four features are contested, for different reasons:

    BMI                 carries most of the lever tier, but a patient changes
                        diet and activity and weight follows
    NoDocbcCost         records a cost barrier to care, not an act
    HvyAlcoholConsump   a lever by guideline, but the audited generator never
                        varies it
    HighBP, HighChol    treatable, or downstream of BMI and therefore indicators

Reads the dumps through depgraph.paths, so it picks up the newest run wherever it was
written. No model is loaded and no counterfactual is regenerated.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import depgraph.nodes as nodes  # noqa: E402
from depgraph.audit import summarise  # noqa: E402
from depgraph.paths import find_dump  # noqa: E402
from depgraph.runlog import RunLog  # noqa: E402

# label -> {feature: new tier}. The empty dict is the paper's own assignment.
SCENARIOS = [
    ("as published", {}),
    ("BMI -> treatable", {"BMI": "treatable"}),
    ("BMI -> indicator", {"BMI": "indicator"}),
    ("NoDocbcCost -> immutable", {"NoDocbcCost": "immutable"}),
    ("HvyAlcoholConsump -> immutable", {"HvyAlcoholConsump": "immutable"}),
    ("HighBP, HighChol -> indicator", {"HighBP": "indicator", "HighChol": "indicator"}),
    ("BMI -> treatable, NoDocbcCost -> immutable",
     {"BMI": "treatable", "NoDocbcCost": "immutable"}),
]


def load():
    changes = defaultdict(set)
    with open(find_dump("raw_cf_changes.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            changes[(r["query_i"], r["cf_k"])].add(r["feature"])
    keys = []
    with open(find_dump("raw_cf_index.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            keys.append((r["query_i"], r["cf_k"]))
    return [changes[k] for k in keys]


def main() -> None:
    log = RunLog("tier_sensitivity")
    per_cf = load()
    original = dict(nodes.TIER)

    print(f"\n{len(per_cf)} counterfactuals, "
          f"{sum(len(c) for c in per_cf)} changes\n")
    hdr = f"{'scenario':<44}{'narrow role':>13}{'narrow edge':>13}{'broad edge':>12}"
    print(hdr)
    print("-" * len(hdr))

    rows = []
    for label, override in SCENARIOS:
        nodes.TIER.clear()
        nodes.TIER.update(original)
        nodes.TIER.update(override)
        r = summarise(per_cf, reading="narrow", rule="role")["cf_unsupported"]
        e = summarise(per_cf, reading="narrow", rule="edge")["cf_unsupported"]
        b = summarise(per_cf, reading="broad", rule="edge")["cf_unsupported"]
        rows.append({"scenario": label, "narrow_role": r, "narrow_edge": e, "broad_edge": b})
        print(f"{label:<44}{r:>13}{e:>13}{b:>12}")

    nodes.TIER.clear()
    nodes.TIER.update(original)

    base = rows[0]
    print("\nchange against the published assignment")
    worse = True
    for r in rows[1:]:
        d = r["narrow_edge"] - base["narrow_edge"]
        print(f"    {r['scenario']:<44}{d:+6d}  (narrow, edge rule)")
        if d < 0:
            worse = False
    print()
    if worse:
        print("Every reassignment RAISES the unsupported count. The published")
        print("assignment is therefore the one least favourable to the paper's own")
        print("conclusion, and a reviewer who disputes a tier is asking for a change")
        print("that would strengthen the finding.")
    else:
        print("At least one reassignment LOWERS the unsupported count. The")
        print("conservativeness claim in Section VII does not hold as stated and")
        print("must be qualified.")

    out = find_dump("raw_cf_changes.csv").parent / "tier_sensitivity.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\n-> {out}")
    log.finish()


if __name__ == "__main__":
    main()
