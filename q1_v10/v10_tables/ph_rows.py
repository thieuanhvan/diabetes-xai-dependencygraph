"""Tables S23-S26 rows from posthoc_b_results.json: v9 file (checked against the printed v9 tables), then v10."""
import json
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")
O9 = "D:/20-study/uit/research/diabetesxai/paper7/outputs/"
F = "q1_ext_b_posthoc/analysis/posthoc_b_results.json"


def tr(x, k=4):
    return math.trunc(round(float(x) * 10 ** k, 6)) / 10 ** k


def f(x, k=4):
    return f"{tr(x, k):.{k}f}".replace("-", "−")


def sg(x, k=4):
    v = tr(x, k)
    return ("+" if v > 0 else ("" if v < 0 else "")) + f(x, k)


def ci(c, k=4):
    return f"[{f(c[0], k)}, {f(c[1], k)}]"


def pv(p):
    return "< 0.0001" if p < 0.0001 else f(p)


def rule(r):
    return {"rule not met": "not met", "rule met": "met", "rule undecided": "undecided"}[r]


def tables(path):
    d = json.load(open(path, encoding="utf-8"))
    seeds = [str(s) for s in d["seed_screen"]["accepted"]]
    P = d["per_seed"]
    out = []
    # S23
    out.append("S23")
    for r in d["seed_screen"]["seeds_tried"]:
        acc = "yes" if r["accepted"] else "no (last hidden layer dead; no eligible patient)"
        out.append(f"| {r['order']} | {r['seed']} | {', '.join(map(str, r['alive_init']))} | {', '.join(map(str, r['alive_trained']))} | {f(r['test_auc'])} | {r['eligible_p_ge_0_5']:,} | {acc} |")
    out.append("consts " + str([(r["seed"], f(r["test_p_min"])) for r in d["seed_screen"]["seeds_tried"] if not r["accepted"]]))
    # S24
    row = lambda name, vals: f"| {name} | " + " | ".join(vals) + " |"  # noqa: E731
    out.append("S24")
    out.append(row("Test AUC", [f(P[s]["model_info"]["test_auc"]) for s in seeds]))
    out.append(row("Coverage, published / lock / route-aware (of 200)", [f"{P[s]['published']['coverage']['x']} / {P[s]['lock']['coverage']['x']} / {P[s]['route']['coverage']['x']}" for s in seeds]))
    out.append(row("Valid among requested, published / lock", [f"{f(P[s]['published']['valid_among_requested']['est'])} / {f(P[s]['lock']['valid_among_requested']['est'])}" for s in seeds]))
    v = []
    for s in seeds:
        h = P[s]["rules_descriptive"]["H4_rule"]["fully_unactionable"]
        v.append(f"{f(h['est'])} ({h['n']}) {ci(h['ci99'])}")
    out.append(row("Fully unactionable (n patients) [99% interval]", v))
    out.append(row("Indicator share vs movability null", [f"{f(P[s]['rules_descriptive']['H4_rule']['movability_null']['T_mean_oshare'])} vs {f(P[s]['rules_descriptive']['H4_rule']['movability_null']['null_mean_of_means'])}" for s in seeds]))
    out.append(row("Movability p", [pv(P[s]["rules_descriptive"]["H4_rule"]["movability_null"]["p"]) for s in seeds]))
    out.append(row("H4 rule", [rule(P[s]["rules_descriptive"]["H4_rule"]["reading"]) for s in seeds]))
    out.append(row("Δ valid [99% interval]", [f"{sg(P[s]['rules_descriptive']['H5_rule']['delta_valid_among_requested']['est'])} {ci(P[s]['rules_descriptive']['H5_rule']['delta_valid_among_requested']['ci99'])}" for s in seeds]))
    out.append(row("Lock coverage [99% interval]", [f"{f(P[s]['rules_descriptive']['H5_rule']['lock_coverage_point'])} {ci(P[s]['rules_descriptive']['H5_rule']['lock_coverage_cp99'])}" for s in seeds]))
    out.append(row("H5 rule", [rule(P[s]["rules_descriptive"]["H5_rule"]["reading"]) for s in seeds]))
    # S25
    out.append("S25")
    out.append(row("Published runs valid before / after rounding", [f"{f(P[s]['published']['runs']['valid_before_rounding'])} / {f(P[s]['published']['runs']['valid_after_rounding'])}" for s in seeds]))
    out.append(row("Published leakage (ADA, k = 1)", [f(P[s]["published"]["leak_ada_k1"]["est"]) for s in seeds]))
    out.append(row("Published outputs changing GenHlth", [f"{P[s]['published']['feature_change_counts'].get('GenHlth', 0)} of {P[s]['published']['n_outputs']}" for s in seeds]))
    out.append(row("Route-aware touch indicator", [f(P[s]["route"]["touch"]["est"]) for s in seeds]))
    out.append(row("Route-aware leakage", [f(P[s]["route"]["leak_ada_k1"]["est"]) for s in seeds]))
    out.append(row("Route-aware fully unactionable", [f(P[s]["route"]["fully"]["est"]) for s in seeds]))
    v = []
    for s in seeds:
        t = P[s]["rules_descriptive"]["S_route_vs_lock_best_kept_cost_TOST"]
        n = t.get("n_paired", t.get("n", 0))
        v.append(f"{t['reading']} ({n} pair{'s' if n != 1 else ''})")
    out.append(row("Route-aware vs lock cost (TOST)", v))
    out.append("lock valid before rounding: " + str({s: (f(P[s]['lock']['runs']['valid_before_rounding']), f(P[s]['lock']['runs']['valid_after_rounding'])) for s in seeds}))
    out.append("lock patients valid before rounding: " + str({s: P[s]['lock']['runs'].get('patients_valid_before_rounding') for s in seeds}))
    # S26
    q = d["pooled"]
    fu, dv, lc, mv = q["fully_unactionable"], q["delta_valid_among_requested"], q["lock_coverage"], q["movability_null_units_as_patients"]
    out.append("S26")
    out.append(f"units {q['n_units']} patients {q['n_test_patients']:,}")
    out.append(f"| Fully unactionable, published ({fu['n_units']} units with an output, {fu['units_without_output']} without) | {f(fu['est'])} | {ci(fu['ci95'])} | {ci(fu['ci99'])} | lower {f(fu['lower_one_sided_99'])} |")
    out.append(f"| Indicator share vs movability null (units as patients) | {f(mv['T_mean_oshare'])} vs {f(mv['null_mean_of_means'])} | – | – | p {pv(mv['p'])} |")
    out.append(f"| Δ valid among requested, lock − published | {sg(dv['est'])} | {ci(dv['ci95'])} | {ci(dv['ci99'])} | lower {f(dv['lower_one_sided_99'])} |")
    out.append(f"| Lock coverage | {f(lc['est'])} | {ci(lc['ci95'])} | {ci(lc['ci99'])} | lower {f(lc['lower_one_sided_99'])} |")
    out.append(f"| Seeds meeting the H4 rule; the H5 rule | {q['seeds_meeting_H4_rule']} of 5; {q['seeds_meeting_H5_rule']} of 5 | – | – | – |")
    sp = q["per_seed_spread"]
    out.append(f"| Per-seed fully unactionable: median (minimum to maximum) | {f(sp['fully_unactionable']['median'])} ({f(sp['fully_unactionable']['min'])} to {f(sp['fully_unactionable']['max'])}) | – | – | – |")
    out.append(f"| Per-seed Δ valid: median (minimum to maximum) | {sg(sp['delta_valid_among_requested']['median'])} ({sg(sp['delta_valid_among_requested']['min'])} to {sg(sp['delta_valid_among_requested']['max'])}) | – | – | – |")
    out.append(f"| Per-seed lock coverage: median (minimum to maximum) | {f(sp['lock_coverage']['median'])} ({f(sp['lock_coverage']['min'])} to {f(sp['lock_coverage']['max'])}) | – | – | – |")
    out.append("H4 readings " + str(q["H4_rule_readings"]))
    out.append("published n_outputs " + str({s: P[s]['published']['n_outputs'] for s in seeds}))
    return out


which = sys.argv[1] if len(sys.argv) > 1 else "v10"
path = O9 + F if which == "v9" else O9 + "p5_v10/outputs/" + F
print("\n".join(tables(path)))
