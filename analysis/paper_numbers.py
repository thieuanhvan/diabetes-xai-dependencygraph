"""Print every number the manuscript quotes, in the order the sections need them.

Standalone: `python analysis/paper_numbers.py`

Reads the dumps through depgraph.paths, so it picks up the newest run wherever it was
written. Nothing is regenerated. Paste the whole output into the manuscript
thread and every figure in Sections V and VI can be updated in one pass.
"""
from __future__ import annotations

import csv
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from depgraph.audit import classify, summarise  # noqa: E402
from depgraph.nodes import TIER  # noqa: E402
from depgraph.paths import find_dump  # noqa: E402
from depgraph.runlog import RunLog  # noqa: E402

CF_PER_QUERY = 5


def rule(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def pct(a, b):
    return f"{a}/{b} = {a / b * 100:.1f}%" if b else "n/a"


def main() -> None:
    log = RunLog("paper_numbers")

    changes = defaultdict(dict)          # (q, k) -> {feature: (before, after)}
    with open(find_dump("raw_cf_changes.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            changes[(int(r["query_i"]), int(r["cf_k"]))][r["feature"]] = (
                float(r["x_before"]), float(r["x_after"]))

    index = []
    with open(find_dump("raw_cf_index.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            index.append((int(r["query_i"]), int(r["cf_k"]), int(r["valid"])))

    keys = [(q, k) for q, k, _ in index]
    per_cf = [set(changes[key]) for key in keys]
    valid = {(q, k): v for q, k, v in index}
    n_cf = len(index)
    n_chg = sum(len(changes[key]) for key in keys)
    patients = sorted({q for q, _ in keys})

    # ---------------------------------------------------------------- Section V-A
    rule("SECTION V-A  reproduction")
    print(f"counterfactuals                  : {n_cf}")
    print(f"patients (queries)               : {len(patients)}")
    print(f"total counterfactual changes     : {n_chg}")
    print(f"counterfactuals with no change   : {sum(1 for key in keys if not changes[key])}")
    nocf = [q for q in patients
            if all(not changes[(q, k)] for k in range(CF_PER_QUERY) if (q, k) in changes)]
    print(f"queries with no counterfactual   : {len(nocf)}")
    print(f"mean changes per counterfactual  : {n_chg / n_cf:.2f}")

    # ---------------------------------------------------------------- Section V-B
    rule("SECTION V-B  where the changes land (Table IV)")
    tiers = Counter()
    for key in keys:
        for f in changes[key]:
            tiers[TIER.get(f, "unknown")] += 1
    print(f"{'Tier':<24}{'Changes':>9}{'Share':>9}")
    for t in ("lever", "treatable", "indicator", "immutable", "unknown"):
        if tiers[t]:
            print(f"{t:<24}{tiers[t]:>9}{tiers[t] / n_chg * 100:>8.1f}%")
    print(f"{'TOTAL':<24}{n_chg:>9}{100.0:>8.1f}%")

    print("\nmost frequently recommended features")
    freq = Counter(f for key in keys for f in changes[key])
    for f, n in freq.most_common(8):
        print(f"    {f:<22}{n:>6}   ({TIER.get(f, '?')})")

    print("\nindicator tier detail")
    for f in ("GenHlth", "PhysHlth", "MentHlth", "DiffWalk"):
        rows = [(key, v) for key in keys for g, v in changes[key].items() if g == f]
        pts = {key[0] for key, _ in rows}
        deltas = [abs(v[1] - v[0]) for _, v in rows]
        if rows:
            print(f"    {f:<10} {len(rows):>4} changes, {len(pts):>4}/{len(patients)} patients "
                  f"({len(pts) / len(patients) * 100:.0f}%), mean move {st.mean(deltas):.2f}")
        else:
            print(f"    {f:<10}    0 changes, never varied")

    print("\nimmutable / SES proxy detail")
    for f in ("Income", "Education"):
        print(f"    {f:<10} {freq[f]:>4} changes")
    print(f"    Income + Education = {freq['Income'] + freq['Education']}")

    # ---------------------------------------------------------------- Section V-C
    rule("SECTION V-C  applying the audit rule")
    for reading in ("narrow", "broad"):
        for r in ("role", "edge"):
            s = summarise(per_cf, reading=reading, rule=r)
            print(f"{reading:<7}{r:<6} touching {s['cf_touching_target']:>4}   "
                  f"unsupported {s['cf_unsupported']:>4}   "
                  f"({pct(s['cf_unsupported'], s['cf_touching_target'])} of those touching)")
    narrow = summarise(per_cf)
    touch = narrow["cf_touching_target"]
    print(f"\ncounterfactuals touching an indicator : {pct(touch, n_cf)}")
    print(f"fully unactionable                    : {pct(narrow['cf_fully_unactionable'], n_cf)}")

    role_u = {key for key, S in zip(keys, per_cf)
              if classify(S, rule="role")["unsupported"]}
    edge_u = {key for key, S in zip(keys, per_cf)
              if classify(S, rule="edge")["unsupported"]}
    pure = {key for key, S in zip(keys, per_cf) if classify(S)["fully_unactionable"]}
    print(f"caught only by the edge rule          : {len(edge_u - role_u)}")
    pat = Counter()
    for key in edge_u - role_u:
        S = changes[key]
        lev = " ".join(sorted(f for f in S if TIER.get(f) == "lever"))
        tgt = " ".join(sorted(f for f in S if TIER.get(f) == "indicator"))
        pat[(lev, tgt)] += 1
    for (lev, tgt), n in pat.most_common(5):
        print(f"    {n:>4}  pulls [{lev}] wants [{tgt}]")

    print(f"\npatient-level")
    print(f"    patients with >=1 fully unactionable CF : "
          f"{pct(len({q for q, _ in pure}), len(patients))}")
    print(f"    patients with >=1 role-unsupported CF   : "
          f"{pct(len({q for q, _ in role_u}), len(patients))}")
    print(f"    patients with >=1 edge-unsupported CF   : "
          f"{pct(len({q for q, _ in edge_u}), len(patients))}")

    # ---------------------------------------------------------------- Section V-D
    rule("SECTION V-D  what tempers this")
    by_patient = defaultdict(int)
    for q, _ in pure:
        by_patient[q] += 1
    worst = max(by_patient.values()) if by_patient else 0
    print(f"max fully unactionable CFs for one patient : {worst} of {CF_PER_QUERY}")
    print(f"patients where ALL {CF_PER_QUERY} are unactionable    : "
          f"{sum(1 for v in by_patient.values() if v == CF_PER_QUERY)}")
    lever_backed = {q for (q, k), S in zip(keys, per_cf)
                    if any(TIER.get(f) == "lever" for f in S)}
    print(f"patients with >=1 lever-backed CF          : "
          f"{pct(len(lever_backed), len(patients))}")
    no_lever = sorted(set(patients) - lever_backed)
    if no_lever:
        print(f"  WARNING: {len(no_lever)} patient(s) receive no lever-backed "
              f"counterfactual at all: {no_lever}")
        for q in no_lever:
            for k in range(CF_PER_QUERY):
                S = sorted(changes.get((q, k), {}))
                tiers_ = [TIER.get(f, "?") for f in S]
                print(f"      patient {q} cf {k}: {S or '(no change)'}  {tiers_}")
        clin = {q for q in no_lever
                if any(TIER.get(f) in ("lever", "treatable")
                       for k in range(CF_PER_QUERY) for f in changes.get((q, k), {}))}
        print(f"  of those, {len(clin)} still receive a treatable (clinician-mediated) "
              f"option, {len(set(no_lever) - clin)} receive nothing actionable at all")

    # ---------------------------------------------------------------- Section V-E
    rule("SECTION V-E  both readings")
    ind = tiers["indicator"]
    trt = tiers["treatable"]
    print(f"narrow (indicators only)      : {pct(ind, n_chg)}")
    print(f"broad  (indicators+treatable) : {pct(ind + trt, n_chg)}")

    # ---------------------------------------------------------------- Section VI-B
    rule("SECTION VI-B  why it is free")
    grp_ind = [valid[key] for key, S in zip(keys, per_cf)
               if any(TIER.get(f) == "indicator" for f in S)
               and not any(TIER.get(f) == "lever" for f in S)]
    grp_lev = [valid[key] for key, S in zip(keys, per_cf)
               if any(TIER.get(f) == "lever" for f in S)]
    print(f"moves an indicator, no lever : validity {st.mean(grp_ind):.3f}  (n = {len(grp_ind)})")
    print(f"moves a lever                : validity {st.mean(grp_lev):.3f}  (n = {len(grp_lev)})")

    # ---------------------------------------------------------------- Table V
    rule("SECTION VI / TABLE V  five-seed sweep")
    sweep = find_dump("seed_sweep.csv", required=False)
    if sweep is None:
        print("seed_sweep.csv not found. Run run_seed_sweep.py.")
    else:
        rows = list(csv.DictReader(open(sweep, newline="")))
        cols = rows[0].keys()
        if "narrow_edge_unsupported_cfs" not in cols:
            print("WARNING: this seed_sweep.csv predates the edge rule "
                  "(no narrow_edge_* columns). Re-run run_seed_sweep.py.")
        pub = [r for r in rows if r["config"] == "published"]
        gph = [r for r in rows if r["config"] == "graph"]
        def col(rs, c, cast=float):
            return [cast(r[c]) for r in rs] if c in rs[0] else []
        for label, c in [("validity", "validity"), ("actionability", "actionability"),
                         ("mean changes per CF", "mean_changes_per_cf")]:
            p, g = col(pub, c), col(gph, c)
            if p and g:
                print(f"{label:<22} published {st.mean(p):.4f}   graph {st.mean(g):.4f}")
        tc = col(pub, "total_changes")
        if tc:
            print(f"{'mean changes per CF':<22} published {st.mean(tc) / n_cf:.2f}   "
                  f"graph {st.mean(col(gph, 'total_changes')) / n_cf:.2f}")
        d = [g - p for p, g in zip(col(pub, "validity"), col(gph, "validity"))]
        if d:
            print(f"\ndelta validity: mean {st.mean(d):+.4f}  sd {st.stdev(d):.4f}  "
                  f"min {min(d):+.4f}  max {max(d):+.4f}  positive in {sum(x > 0 for x in d)}/{len(d)}")
        print("\nper-seed ranges (published config)")
        for c in ("indicator_changes", "unsupported_cfs", "narrow_role_unsupported_cfs",
                  "narrow_edge_unsupported_cfs", "broad_role_unsupported_cfs",
                  "broad_edge_unsupported_cfs", "pure_indicator_cfs",
                  "queries_no_cf", "total_changes", "auc"):
            v = col(pub, c)
            if v:
                lo, hi = min(v), max(v)
                fmt = "{:.4f}" if c == "auc" else "{:.0f}"
                print(f"    {c:<32} {fmt.format(lo)} to {fmt.format(hi)}")
        ru = col(pub, "narrow_role_unsupported_cfs")
        eu = col(pub, "narrow_edge_unsupported_cfs")
        if ru and eu:
            extra = [e - r for r, e in zip(ru, eu)]
            print(f"    {'edge-only catches':<32} {min(extra):.0f} to {max(extra):.0f} "
                  f"(mean {st.mean(extra):.1f})")
        print("\nqueries left with no CF, graph config: "
              f"{[int(r['queries_no_cf']) for r in gph]}")

    log.finish()


if __name__ == "__main__":
    main()
