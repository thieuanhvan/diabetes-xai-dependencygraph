"""Re-audit already-dumped counterfactuals under every rule / reading combination.

Standalone: `python analysis/audit_rules.py`
Reads outputs/raw_cf_changes.csv and outputs/raw_cf_index.csv, which
run_audit_dump.py produces. No model is loaded and no counterfactual is
regenerated, so this is instant and can be re-run whenever the edge set or the
tier assignment changes.

Writes outputs/audit_rule_comparison.csv and outputs/audit_rule_diff.csv.
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from depgraph.audit import classify, summarise  # noqa: E402
from depgraph.paths import find_dump, write_dir  # noqa: E402
from depgraph.runlog import RunLog  # noqa: E402
from depgraph.nodes import TIER  # noqa: E402


def load(out_dir: Path | None = None):
    """-> (keys, {(query_i, cf_k): set(features changed)})

    Every CF is covered, including those with no recorded change: they appear in
    the index but not in the changes file. Inputs are resolved through
    depgraph.paths.find_dump so the file actually read is printed, not assumed.
    """
    if out_dir is None:
        chg_path = find_dump("raw_cf_changes.csv")
        idx_path = find_dump("raw_cf_index.csv")
    else:
        chg_path, idx_path = Path(out_dir) / "raw_cf_changes.csv", Path(out_dir) / "raw_cf_index.csv"
    changes = defaultdict(set)
    with open(chg_path, newline="") as fh:
        for r in csv.DictReader(fh):
            changes[(r["query_i"], r["cf_k"])].add(r["feature"])
    keys = []
    with open(idx_path, newline="") as fh:
        for r in csv.DictReader(fh):
            keys.append((r["query_i"], r["cf_k"]))
    return keys, changes


def main(out_dir: Path | None = None) -> None:
    log = RunLog("audit_rules")
    keys, changes = load(out_dir)
    out_dir = Path(out_dir) if out_dir is not None else write_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    cfs = [changes[k] for k in keys]
    print(f"counterfactuals: {len(cfs)}   total changes: {sum(len(c) for c in cfs)}\n")

    rows = []
    for reading in ("narrow", "broad"):
        for rule in ("role", "edge"):
            for grades in (None, "ABC"):
                if rule == "role" and grades is not None:
                    continue  # the role rule ignores E, so grades are meaningless
                rows.append(summarise(cfs, reading=reading, rule=rule, grades=grades))

    hdr = ["reading", "rule", "grades", "cf_touching_target", "cf_unsupported",
           "unsupported_changes", "cf_fully_unactionable"]
    w = [max(len(h), 12) for h in hdr]
    print("  ".join(h.ljust(x) for h, x in zip(hdr, w)))
    for r in rows:
        print("  ".join(str(r[h]).ljust(x) for h, x in zip(hdr, w)))

    with open(out_dir / "audit_rule_comparison.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)

    # The counterfactuals the edge rule catches and the role rule does not.
    diff = []
    for k, S in zip(keys, cfs):
        a = classify(S, reading="narrow", rule="role")
        b = classify(S, reading="narrow", rule="edge")
        if b["unsupported"] and not a["unsupported"]:
            diff.append({
                "query_i": k[0], "cf_k": k[1],
                "changed": " ".join(sorted(S)),
                "levers_pulled": " ".join(sorted(f for f in S if TIER.get(f) == "lever")),
                "unsupported_targets": " ".join(b["unsupported_targets"]),
            })
    with open(out_dir / "audit_rule_diff.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(diff[0]) if diff else
                            ["query_i", "cf_k", "changed", "levers_pulled", "unsupported_targets"])
        wr.writeheader()
        wr.writerows(diff)

    print(f"\ncaught by the edge rule but NOT by the role rule: {len(diff)} counterfactuals")
    pat = defaultdict(int)
    for d in diff:
        pat[(d["levers_pulled"], d["unsupported_targets"])] += 1
    for (lev, tgt), n in sorted(pat.items(), key=lambda kv: -kv[1]):
        print(f"    {n:4d}  pulls [{lev}] but wants to move [{tgt}]")
    print(f"\n-> {out_dir/'audit_rule_comparison.csv'}\n-> {out_dir/'audit_rule_diff.csv'}")
    log.finish()


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
