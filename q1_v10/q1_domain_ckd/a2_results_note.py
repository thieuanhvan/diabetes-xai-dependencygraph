"""Render the A2 results note (English, results only) from a2_analysis/results_<cohort>.json.

Numbers truncated to 4 decimals (rulebook 5.5), never rounded. Usage: python -I a2_results_note.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a2_domain as D  # noqa: E402

t = D.trunc


def iv(x):
    return f"[{t(x[0])}, {t(x[1])}]"


def block(r, title):
    o = r["O_A1_fully_unactionable_dice_published"]
    n2 = r["O_A2_movability_null"]
    a3 = r["O_A3_valid_among_requested_lock_minus_published"]
    a5 = r["O_A5_dist_lock_minus_route_exhaustive"]
    a4 = r["O_A4_route_strictly_better_than_lock"]
    nd = r["near_degenerate_check"]
    cov = r["coverage_dice"]
    L = [f"## {title}", "",
         f"- Cohort: {r['n_cohort']} test patients with p >= 0.5 (eligible {r['eligible']}); test AUC {t(r['test_auc'])}.",
         f"- Pre-generator property (S1): {t(r['pre_generator_single_nonindicator_flip_share'])} of cohort patients can be "
         f"flipped by one non-indicator change (95% CP {iv(r['pre_generator_single_nonindicator_flip']['cp95'])}).",
         f"- Near-degenerate check (computed from the cohort before any generator ran): supporting levers "
         f"{', '.join(f'{k} movable for {t(v)}' for k, v in nd['share_cohort_movable'].items())}; "
         f"degenerate = {nd['degenerate']}, near-degenerate = {nd['near_degenerate']}.", "",
         "| Hypothesis | Estimate | Interval | Verdict |", "|---|---|---|---|",
         f"| H1 (i) O-A1 fully unactionable, DiCE random, published | {t(o['est'])} | one-sided 99% bound {t(o['lower_one_sided_99'])} "
         f"(two-sided 99% {iv(o['ci99'])}) | component (i) {'passes' if r['H1']['component_i_replication_lower99_gt_0.10'] else 'fails'} |",
         f"| H1 (ii) O-A2 movability null | mean O-share T = {t(n2['T_mean_oshare'])} (null mean {t(n2['null_mean_of_means'])}) | "
         f"p = {t(n2['p'])} ({n2['draws']} draws) | component (ii) {'passes' if r['H1']['component_ii_p_lt_0.01'] else 'fails'} |",
         f"| **H1** | | | **{r['H1']['verdict']}** |",
         f"| H2 O-A3 valid among requested, lock - published | {t(a3['est'])} | one-sided 99% bound {t(a3['lower_one_sided_99'])} "
         f"(two-sided 99% {iv(a3['ci99'])}); lock coverage {t(cov['lock']['share'])} (99% CP {iv(cov['lock']['cp99'])}) | **{r['H2']['verdict']}** |",
         f"| H3 O-A5 best distance, lock - route-aware, exhaustive | {t(a5['est'])} (n pairs {a5['n']}) | 98% {iv(a5['ci98'])}, delta 0.05 | "
         f"**{r['H3']['verdict']}**{' (near-degenerate flag)' if r['H3']['near_degenerate_flag'] else ''} |", "",
         f"Preregistered reading: H1 {r['H1']['verdict']}, H2 {r['H2']['verdict']}, H3 {r['H3']['verdict']}. "
         f"{r['H3']['reading'].capitalize()}. If the one-sided bounds were replaced by two-sided 99% bounds the verdicts would be "
         f"H1 {r['H1']['verdict_if_two_sided_99']}, H2 {r['H2']['verdict_if_two_sided_99']}.", "",
         "Secondaries paired with H1-H3 (95% intervals, exploratory):", "",
         f"- O-share, DiCE published: {t(r['O_share_dice_published']['est'])} {iv(r['O_share_dice_published']['ci95'])}; "
         f"touch share {t(r['touch_share_dice_published']['est'])} {iv(r['touch_share_dice_published']['ci95'])}.",
         f"- Valid among requested: published {t(a3['published_valid_among_requested'])}, lock {t(a3['lock_valid_among_requested'])} "
         f"(relative loss {t(a3['relative_loss'])}), route-aware {t(r['route_cost_dice_route_minus_published']['route_valid_among_requested'])}; "
         f"route - published {t(r['route_cost_dice_route_minus_published']['est'])} {iv(r['route_cost_dice_route_minus_published']['ci95'])}, "
         f"mean regeneration rounds {t(r['route_cost_dice_route_minus_published']['mean_rounds'])}.",
         f"- DiCE coverage (>= 1 valid CF): published {t(cov['published']['share'])}, lock {t(cov['lock']['share'])}, "
         f"route-aware {t(cov['route']['share'])} {iv(cov['route']['cp95'])}.",
         f"- O-A4 route-aware strictly better than lock (exhaustive): {a4['x']}/{a4['n_pairs']} = {t(a4['share'])} {iv(a4['cp95'])}; "
         f"O-A5 exactly zero for {t(a5['share_exactly_zero'])} of pairs; route-only {a5['n_route_only']}, lock-only {a5['n_lock_only']} patients."]
    ex = r["exhaustive_costs"]
    for m in ("published", "lock", "route", "capped"):
        e = ex[m]
        L.append(f"- Exhaustive {m}: coverage {t(e['coverage'])} {iv(e['cp95'])}, best changes {t(e['best_changes'].get('est'))}, "
                 f"best distance {t(e['best_dist'].get('est'))}"
                 + (f"; distance minus published {t(e['dist_minus_published']['est'])} {iv(e['dist_minus_published']['ci95'])}" if 'dist_minus_published' in e else "")
                 + (f"; distance minus route-aware {t(e['dist_minus_route']['est'])} {iv(e['dist_minus_route']['ci95'])}" if e.get('dist_minus_route') else "") + ".")
    L.append("- Leakage (share of a patient's counterfactuals that leak, published mode), by reading:")
    for gen, rd in r["leakage_published"].items():
        parts = [f"{k} {t(v['est'])} {iv(v['ci95'])}" for k, v in rd.items()]
        L.append(f"  - {gen}: " + "; ".join(parts) + ".")
    L.append(f"- Change sizes of supported indicator moves (steps = GenHlth levels or PHQ-9 bands; cap = 1 per lever); "
             f"DiCE route-aware counterfactuals meeting the cap: {t(r['dice_route_share_meeting_cap'])}.")
    for k, v in r["change_sizes_supported_indicator_moves"].items():
        L.append(f"  - {k}: n {v['n']}, steps {v['steps_distribution']}, within cap {t(v['share_within_cap'])}.")
    L.append("- A-Q4 cross-guideline agreement (indicator-touching CFs, published; verdict under ADA vs KDIGO, k = 1):")
    for gen, v in r["A_Q4_cross_guideline_agreement"].items():
        L.append(f"  - {gen}: n CF {v['n_cf']} ({v['n_patients']} patients), raw agreement {t(v['raw_agreement'])} {iv(v['raw_agreement_ci95'])}, "
                 f"kappa {t(v['kappa'])} {iv(v['kappa_ci95'])}; supported under KDIGO {t(v['supported_kdigo'])}, under ADA {t(v['supported_ada'])}; reading: {v['reading']}.")
    for c, v in r["per_cycle_dice_published"].items():
        L.append(f"- Cycle {c} (n {v['O_A1']['n']}): O-A1 {t(v['O_A1']['est'])} {iv(v['O_A1']['ci95'])}, O-share {t(v['O_share']['est'])} {iv(v['O_share']['ci95'])}.")
    dc = r["distinct_cfs_per_patient_dice_published"]
    L.append(f"- Distinct counterfactuals per patient (DiCE published, 5 seeds): {t(dc['est'])} {iv(dc['ci95'])}.")
    sc = r["software_checks"]
    L.append("- Software checks: " + ", ".join(f"{k} = {v}" for k, v in sc.items()) + ".")
    return L


def main():
    A = D.OUT / "a2_analysis"
    res = {c: json.loads((A / f"results_{c}.json").read_text(encoding="utf-8"))
           for c in ("main", "less_exposed") if (A / f"results_{c}.json").exists()}
    L = ["# P7 Q1 extension, step A2: CKD primary results (prereg v3)", "",
         f"Written {datetime.now():%d/%m/%Y %H:%M} by a2_results_note.py from a2_analysis/results_*.json. Results only. "
         "Pooled NHANES 2017-2023, XGBoost (P4 configuration), roles derived from the graph, KDIGO 2024 agreed graph "
         "(route-aware primary reading k = 1). Numbers truncated to four decimals.", ""]
    if "main" in res:
        L += block(res["main"], "Main cohort (primary)") + [""]
    if "less_exposed" in res:
        L += block(res["less_exposed"], "Less-exposed cohort (secondary: KIQ022 = 1 excluded)") + [""]
    for c in ("main", "less_exposed"):
        p = A / f"sparql_audit_{c}.json"
        if p.exists():
            s = json.loads(p.read_text(encoding="utf-8"))
            L.append(f"Python vs SPARQL on all audited counterfactuals ({c}): "
                     + "; ".join(f"{k}: {v['disagreements']} disagreements over {v['n_distinct_change_sets']} distinct change sets "
                                 f"({v['n_cf']} CFs)" for k, v in s.items() if k.startswith("audit_")) + ".")
    p = A / "sparql_unit_test.json"
    if p.exists():
        s = json.loads(p.read_text(encoding="utf-8"))
        L.append("Python vs SPARQL unit test (10,000 random change sets per reading): "
                 + "; ".join(f"{k[5:]} {v['disagreements']} disagreements" for k, v in s.items() if k.startswith("test_")) + ".")
    (A / "a2_results_note_en.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
