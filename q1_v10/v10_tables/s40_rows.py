"""Table S40 rows (CKD splits) from results_main.json: v9 check, then v10. Main row from q1_domain_ckd, S-P1 row from ses_freeze."""
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
O9 = "D:/20-study/uit/research/diabetesxai/paper7/outputs/"


def tr(x, k=4):
    return math.trunc(round(float(x) * 10 ** k, 6)) / 10 ** k


def f(x, k=4):
    return f"{tr(x, k):.{k}f}".replace("-", "−")


def pv(p):
    return "< 0.0001" if p < 0.0001 else f(p)


V = {"supported": "S", "not supported": "N", "undecided": "U", "supported (equivalent)": "S", "not supported (not equivalent)": "N"}


def row(name, d):
    a1, a2, a3, a5, a4 = (d["O_A1_fully_unactionable_dice_published"], d["O_A2_movability_null"],
                          d["O_A3_valid_among_requested_lock_minus_published"], d["O_A5_dist_lock_minus_route_exhaustive"],
                          d["O_A4_route_strictly_better_than_lock"])
    return (f"| {name} | {f(d['test_auc'])}; {d['n_cohort']} | {f(a1['est'])} [{f(a1['lower_one_sided_99'])}]; {pv(a2['p'])} | "
            f"{f(a3['est'])} [{f(a3['lower_one_sided_99'])}]; {f(d['H2']['lock_coverage_point'])} | {f(a5['est'])} [{f(a5['ci98'][0])}, {f(a5['ci98'][1])}] | "
            f"{V[d['H1']['verdict']]}, {V[d['H2']['verdict']]}, {V[d['H3']['verdict']]} | {a4['x']}/{a4['n_pairs']} |")


def rows(base):
    out = []
    main = Path(base) / "q1_domain_ckd" / "a2_analysis" / "results_main.json"
    if main.exists():
        out.append(row("Preregistered, split 42", json.load(open(main, encoding="utf-8"))))
    out.append(row("Socio-economic frozen, split 42", json.load(open(Path(base) / "q1_posthoc_ses_splits/ses_freeze/a2_analysis/results_main.json", encoding="utf-8"))))
    extra = []
    for s in (11, 22, 33, 44, 55):
        p = Path(base) / f"q1_posthoc_ses_splits/split_{s}/a2_analysis/results_main.json"
        if p.exists():
            d = json.load(open(p, encoding="utf-8"))
            out.append(row(f"Split {s}", d))
            extra.append((s, d))
        else:
            out.append(f"MISSING split {s}")
    if extra:
        g = lambda key, sub: [x[1][key][sub] for x in extra]  # noqa: E731
        out.append("AUC " + f(min(x[1]["test_auc"] for x in extra)) + "–" + f(max(x[1]["test_auc"] for x in extra))
                   + "; cohorts " + str(min(x[1]["n_cohort"] for x in extra)) + "–" + str(max(x[1]["n_cohort"] for x in extra)))
        out.append("fully " + f(min(g("O_A1_fully_unactionable_dice_published", "est"))) + "–" + f(max(g("O_A1_fully_unactionable_dice_published", "est")))
                   + "; p max " + pv(max(g("O_A2_movability_null", "p"))))
        out.append("dvalid " + f(min(g("O_A3_valid_among_requested_lock_minus_published", "est"))) + "–" + f(max(g("O_A3_valid_among_requested_lock_minus_published", "est")))
                   + "; lower<0 in " + str(sum(1 for v in g("O_A3_valid_among_requested_lock_minus_published", "lower_one_sided_99") if v < 0))
                   + "; cov " + f(min(x[1]["H2"]["lock_coverage_point"] for x in extra)) + "–" + f(max(x[1]["H2"]["lock_coverage_point"] for x in extra)))
        out.append("dist " + f(min(g("O_A5_dist_lock_minus_route_exhaustive", "est"))) + "–" + f(max(g("O_A5_dist_lock_minus_route_exhaustive", "est")))
                   + "; ci98 lo " + f(min(x[1]["O_A5_dist_lock_minus_route_exhaustive"]["ci98"][0] for x in extra)) + "–" + f(max(x[1]["O_A5_dist_lock_minus_route_exhaustive"]["ci98"][0] for x in extra))
                   + "; A4 " + str(min(g("O_A4_route_strictly_better_than_lock", "x"))) + "–" + str(max(g("O_A4_route_strictly_better_than_lock", "x"))))
        out.append("verdicts " + str({s: (d["H1"]["verdict"], d["H2"]["verdict"], d["H3"]["verdict"]) for s, d in extra}))
        k = [x[1]["A_Q4_cross_guideline_agreement"] for x in extra]
        out.append("kappa keys " + str(list(k[0].keys())))
        out.append("leaks " + str({s: sum(v for v in d["software_checks"].values()) for s, d in extra}))
    return out


base = O9 if (len(sys.argv) > 1 and sys.argv[1] == "v9") else O9 + "p5_v10/outputs/"
print("\n".join(rows(base)))
