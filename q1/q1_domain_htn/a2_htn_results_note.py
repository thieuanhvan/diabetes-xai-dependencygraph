"""Write outputs/q1_domain_htn/a2_analysis/a2_results_note_en.md from the A1-HTN and A2-HTN result files.
Numbers truncated (never rounded) to four decimals. Usage: python -I a2_htn_results_note.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from htn_common import OUT, sha256_file, trunc  # noqa: E402

A = OUT / "a2_analysis"
T = lambda x: trunc(x)  # noqa: E731
VARIANTS = [("main", "Main cohort, L1, pooled 2017-2023 (primary)"),
            ("less_exposed", "Less-exposed cohort (BPQ020 = 1 removed; same model)"),
            ("rimm_off", "R-IMM comparison (Income, Education, AnyHealthcare movable upward as in CKD; same model and cohort)"),
            ("l2", "Label L2 (measured or treated), refit"),
            ("no_bpmed", "Refit without participants now taking BP medication"),
            ("no_dx", "Refit without Diabetes, KidneyDisease, Stroke, HeartDiseaseorAttack")]


def ci(d, key="ci95"):
    return f"[{T(d[key][0])}, {T(d[key][1])}]"


def block(r, title, primary):
    L = [f"## {title}", ""]
    if "status" in r:
        return L + [f"- {r['status']}", ""]
    s1 = r["S1_single_nonindicator_flip"]
    L += [f"- Analytic n {r['n_analytic']}; label {r['target']}; test AUC {T(r['test_auc'])}; eligible (p >= 0.5) {r['eligible']}; cohort {r['n_cohort']}; R-IMM applied: {r['r_imm_applied']}.",
          f"- S1 (one non-indicator change flips the prediction, before any generator): {T(s1['share'])} (95% CP [{T(s1['cp95'][0])}, {T(s1['cp95'][1])}]).", ""]
    o1, o2, o3 = r["O_A1_fully_unactionable_dice_published"], r["O_A2_movability_null"], r["O_A3_valid_among_requested_lock_minus_published"]
    L += ["| Hypothesis | Estimate | Interval | Verdict |", "|---|---|---|---|",
          f"| H1-HTN (i) O-A1 fully unactionable, DiCE random, published | {T(o1['est'])} | one-sided 99% lower bound {T(o1['lower_one_sided_99'])}, upper {T(o1['upper_one_sided_99'])} | component (i) {'passes' if r['H1']['component_i_lower99_gt_0.10'] else 'does not pass'} |",
          f"| H1-HTN (ii) O-A2 movability null | T = {T(o2['T_mean_oshare'])} (null mean {T(o2['null_mean_of_means'])}) | p = {T(o2['p'])} ({o2['draws']} draws) | component (ii) {'passes' if r['H1']['component_ii_p_lt_0.01'] else 'does not pass'} |",
          f"| **H1-HTN** | | | **{r['H1']['verdict']}**{'' if primary else ' (descriptive)'} |",
          f"| H2-HTN O-A3 valid among requested, lock - published | {T(o3['est'])} | one-sided 99% lower bound {T(o3['lower_one_sided_99'])}; lock coverage {T(r['H2']['lock_coverage_point'])} | **{r['H2']['verdict']}**{'' if primary else ' (descriptive)'} |",
          f"| H3-HTN | | | **{r['H3']['verdict']}** |", ""]
    osh, tch = r["O_share_dice_published"], r["touch_share_dice_published"]
    L += [f"- O-share {T(osh['est'])} {ci(osh)}; touch share {T(tch['est'])} {ci(tch)}; valid among requested: published {T(o3['published_valid_among_requested'])}, lock {T(o3['lock_valid_among_requested'])}.",
          f"- DiCE coverage (>= 1 valid CF): " + ", ".join(f"{m} {T(v['share'])}" for m, v in r["coverage_dice"].items()) + ".",
          "- Exhaustive search: " + "; ".join(f"{m} coverage {T(v['coverage'])}, best changes {T(v['best_changes']['est'])}, best distance {T(v['best_dist']['est'])}" for m, v in r["exhaustive_costs"].items()) +
          f"; lock distance minus published {T(r['exhaustive_costs']['lock']['dist_minus_published']['est'])} {ci(r['exhaustive_costs']['lock']['dist_minus_published'])}.",
          "- Leakage of published counterfactuals under other authorities (share of a patient's CFs, k = 1): " +
          "; ".join(f"{g}: " + ", ".join(f"{k} {T(v['est'])}" for k, v in d.items()) for g, d in r["leakage_published_other_authorities"].items()) + ".",
          "- Per cycle (DiCE published): " + "; ".join(f"{c} (n {v['O_A1']['n']}) O-A1 {T(v['O_A1']['est'])} {ci(v['O_A1'])}, O-share {T(v['O_share']['est'])}" for c, v in r["per_cycle_dice_published"].items()) + ".",
          f"- Distinct counterfactuals per patient (5 seeds): {T(r['distinct_cfs_per_patient_dice_published']['est'])}; feature change counts (DiCE published): {r['feature_change_counts_dice_published']}.",
          f"- Software checks: {r['software_checks']}; movability null: max subsets per patient {o2['max_subsets_per_patient']}, changes outside the movable set {o2['changes_outside_movable_set']}.", ""]
    return L


def main():
    a1 = json.loads((OUT / "a1_extraction" / "single_extractor_A" / "single_extractor_A.json").read_text(encoding="utf-8"))
    ga = json.loads((OUT / "a1_extraction" / "recall_gate" / "recall_gate_extractorA_claude_v1.json").read_text(encoding="utf-8"))
    gb = json.loads((OUT / "a1_extraction" / "recall_gate" / "recall_gate_extractorB_qwen72b_v2.json").read_text(encoding="utf-8"))
    rent = json.loads((OUT / "a1_extraction" / "extractorB_qwen72b_v2" / "rental_log.json").read_text(encoding="utf-8"))

    def g(x, d):
        return f"{len(x['gate'][d]['recovered_after_quote_check'])}/{len(x['gate'][d]['agreed_x5'])} (before the quotation check {len(x['gate'][d]['recovered_before_quote_check'])})"
    L = ["# P7 Q1 extension, hypertension domain: A1-HTN and A2-HTN results (addendum HTN v3)", "",
         f"Written {datetime.now():%d/%m/%Y %H:%M} by a2_htn_results_note.py. Results only. Numbers truncated to four decimals.", "",
         "## Extraction and gates (A1-HTN)", "",
         f"- Recall gate, extractor A (Claude, prompt v1): **{ga['verdict']}**. HEARTS-D {g(ga, 'gate_who_heartsd')}; MoH 5481 {g(ga, 'gate_moh5481')}; NG28 false-positive pairs {ga['ng28_false_positive_pairs_after_quote_check']}.",
         f"- Recall gate, extractor B (Qwen2.5-72B-Instruct AWQ, prompt v2, vLLM 0.32.0, A100-SXM4-80GB): **{gb['verdict']}**. HEARTS-D {g(gb, 'gate_who_heartsd')}; MoH 5481 {g(gb, 'gate_moh5481')}; NG28 false-positive pairs {gb['ng28_false_positive_pairs_after_quote_check']}.",
         "- Consequence (declared in addendum 5.4, no fallback): the HTN agreed graph, the inter-model agreement gate, H3-HTN and A-Q4-HTN are **not reached**. Extractor B's HTN outputs are hashed and were not opened.",
         f"- Extractor A, descriptive single-extractor graph (not used by any test): {a1['extractorA_passages']} passages, {a1['extractorA_passages_after_quote_check']} pass the quotation check; Concept pairs {a1['extractorA_pairs_after_quote_check']}; NHANES item edges {a1['extractorA_nhanes_item_edges']} (into an indicator: {a1['extractorA_item_edges_into_indicators']}).",
         f"- Test-retest, extractor A: {json.dumps(a1['test_retest_extractorA'])}. Extractor B: not computed (outputs not opened after the failed gate).",
         f"- GPU rental: instance {rent['instance_id']}, {rent['gpu']}, {rent['billed_duration_s']} s billed, total cost {rent['cost_usd']['total']} USD (cap 8 USD); {rent['returned']}/{rent['requests']} requests returned, {rent['finish_reason_length']} truncated, {rent['technical_failures']} technical failures; instance destroyed after the outputs were verified.", ""]
    for v, title in VARIANTS:
        p = A / f"results_{v}.json"
        if p.exists():
            L += block(json.loads(p.read_text(encoding="utf-8")), title, v == "main")
        else:
            L += [f"## {title}", "", "- not run", ""]
    sp = A / "sparql_audit_main.json"
    if sp.exists():
        L += ["## Python-SPARQL check", "", f"- {sp.read_text(encoding='utf-8').strip()}", ""]
    ut = A / "sparql_unit_test.json"
    if ut.exists():
        L += [f"- Unit test: {ut.read_text(encoding='utf-8').strip()}", ""]
    (A / "a2_results_note_en.md").write_text("\n".join(L), encoding="utf-8", newline="\n")
    print("written", sha256_file(A / "a2_results_note_en.md"))


if __name__ == "__main__":
    main()
