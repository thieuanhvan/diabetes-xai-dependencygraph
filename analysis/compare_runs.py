"""Compare two dumped counterfactual runs feature-change by feature-change.

Standalone:
    python analysis/compare_runs.py A.csv B.csv

Why this exists
---------------
Table IV of the paper comes from run_audit_dump.py. The robustness ranges in
Section V-E come from run_seed_sweep.py at the same seed. If those two runs do
not produce the same counterfactuals, the paper is quoting two different
experiments as if they were one, and the reader cannot tell.

run_seed_sweep.py now writes sweep_changes_seed<S>_<config>.csv, so the check is:

    python analysis/compare_runs.py \\
        outputs/raw_cf_changes.csv \\
        <PIPELINE_REPO>/outputs_kg/sweep_changes_seed42_published.csv

IDENTICAL  -> the two scripts agree; quote either.
DIFFERENT  -> they are different configurations, not run-to-run noise, and the
              paper must say which run each number comes from.

The script does not guess which is right. It reports what differs.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from depgraph.nodes import TIER  # noqa: E402
from depgraph.paths import find_dump  # noqa: E402


def load(path: Path):
    """-> {(query_i, cf_k): {feature: (before, after)}}"""
    cfs = defaultdict(dict)
    with open(path, newline="") as fh:
        rd = csv.DictReader(fh)
        need = {"query_i", "cf_k", "feature"}
        missing = need - set(rd.fieldnames or [])
        if missing:
            raise SystemExit(
                f"{path}: not a CF change dump, missing column(s) {sorted(missing)}.\n"
                f"Columns present: {rd.fieldnames}\n"
                f"Expected a file written by run_audit_dump.py or run_seed_sweep.py.")
        has_vals = {"x_before", "x_after"} <= set(rd.fieldnames)
        for r in rd:
            key = (int(r["query_i"]), int(r["cf_k"]))
            cfs[key][r["feature"]] = (
                (round(float(r["x_before"]), 6), round(float(r["x_after"]), 6))
                if has_vals else None)
    return cfs


def tier_counts(cfs):
    c = Counter()
    for feats in cfs.values():
        for f in feats:
            c[TIER.get(f, "unknown")] += 1
    return c


def main(a_path: Path, b_path: Path) -> None:
    A, B = load(a_path), load(b_path)
    na = sum(len(v) for v in A.values())
    nb = sum(len(v) for v in B.values())
    print(f"A  {a_path}\n   {len(A):5d} counterfactuals with changes, {na:5d} changes")
    print(f"B  {b_path}\n   {len(B):5d} counterfactuals with changes, {nb:5d} changes\n")

    ta, tb = tier_counts(A), tier_counts(B)
    print(f"{'tier':<18}{'A':>8}{'B':>8}{'diff':>8}")
    for t in ("lever", "treatable", "indicator", "immutable", "unknown"):
        if ta[t] or tb[t]:
            print(f"{t:<18}{ta[t]:>8}{tb[t]:>8}{tb[t]-ta[t]:>+8}")
    print(f"{'TOTAL':<18}{na:>8}{nb:>8}{nb-na:>+8}\n")

    keys = set(A) | set(B)
    only_a = sorted(set(A) - set(B))
    only_b = sorted(set(B) - set(A))
    differing = sorted(k for k in set(A) & set(B) if A[k] != B[k])

    if not only_a and not only_b and not differing:
        print("IDENTICAL: every counterfactual changes the same features by the "
              "same amounts.")
        print("The two scripts are running the same experiment; either may be quoted.")
        return

    print("DIFFERENT")
    print(f"  counterfactuals only in A : {len(only_a)}")
    print(f"  counterfactuals only in B : {len(only_b)}")
    print(f"  present in both but differing: {len(differing)} "
          f"of {len(set(A) & set(B))} shared")
    for k in differing[:8]:
        fa, fb = A[k], B[k]
        print(f"    query {k[0]:3d} cf {k[1]}: A={sorted(fa)}  B={sorted(fb)}")
    print("\nThis is a configuration difference, not rounding. Decide which run "
          "each reported number comes from and say so in the paper.")


def _resolve(arg: str) -> Path:
    """A path if it exists, otherwise a bare filename looked up in the usual
    output directories."""
    p = Path(arg)
    return p if p.exists() else find_dump(arg)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # The comparison that matters: the Table IV run against the sweep at the
        # same seed. Both resolved, so it does not matter which repo they are in.
        a = _resolve("raw_cf_changes.csv")
        b = _resolve("sweep_changes_seed42_published.csv")
    elif len(sys.argv) == 3:
        a, b = _resolve(sys.argv[1]), _resolve(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(2)
    main(a, b)
