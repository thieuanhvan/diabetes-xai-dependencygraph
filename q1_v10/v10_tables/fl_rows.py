"""Tables S39 and S41 rows: v9 (checked against the printed tables), then v10."""
import json
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")
O9 = "D:/20-study/uit/research/diabetesxai/paper7/outputs/"


def tr(x, k=4):
    return math.trunc(round(float(x) * 10 ** k, 6)) / 10 ** k


def f(x, k=4):
    return f"{tr(x, k):.{k}f}".replace("-", "−")


def sg(x):
    return ("+" if tr(x) > 0 else "") + f(x)


def pv(p):
    return "< 0.0001" if p < 0.0001 else f(p)


def rows(base):
    fl = json.load(open(base + "q1_posthoc_forced_lever/analysis/forced_lever_results.json", encoding="utf-8"))
    ph = json.load(open(base + "q1_ext_b_posthoc/analysis/posthoc_b_results.json", encoding="utf-8"))
    out = ["S39"]
    P = ph["per_seed"]
    for s in ["44", "45", "46", "48", "49"]:
        h4 = P[s]["rules_descriptive"]["H4_rule"]
        fu = h4["fully_unactionable"]
        out.append(f"| {s} | {P[s]['published']['coverage']['x']} / {P[s]['lock']['coverage']['x']} / {P[s]['route']['coverage']['x']} | {f(fu['est'])} [{f(fu['ci99'][0])}, {f(fu['ci99'][1])}] | {pv(h4['movability_null']['p'])} | {sg(P[s]['rules_descriptive']['H5_rule']['delta_valid_among_requested']['est'])} | {h4['reading'].replace('rule ', '')} |")
    sums = [sum(P[s][m]["coverage"]["x"] for s in P) for m in ("published", "lock", "route")]
    q = ph["pooled"]["fully_unactionable"]
    out.append(f"| Pooled | {sums[0]} / {sums[1]} / {sums[2]} of 1,000 | {f(q['est'])} [{f(q['ci99'][0])}, {f(q['ci99'][1])}] | < 0.0001 (descriptive) | not pooled (sign differs between seeds) | met at {ph['pooled']['seeds_meeting_H4_rule']} of 5 seeds |")
    out.append("S41")
    W = fl["wachter"]
    for key, name in (("s44", "Seed 44"), ("s45", "Seed 45"), ("s46", "Seed 46"), ("s48", "Seed 48"), ("s49", "Seed 49"), ("lr", "LR")):
        w = W[key]
        cov = " / ".join(str(round(w[m]["coverage"] * 200)) for m in ("published", "lock", "forced", "lockroute", "route"))
        vb = " / ".join(f(w[m]["valid_before_rounding"]) for m in ("lock", "forced", "route"))
        va = " / ".join(f(w[m]["valid_after_rounding"]) for m in ("lock", "forced", "route"))
        out.append(f"| {name} | {cov} | {vb} | {va} | {f(w['route']['kept']['genhlth'] * 100, 2)}% |")
    c = fl["pooled"]["key_seeds_46_48_49"]
    cv = c["coverage"]
    d = c["delta_G_route_minus_forced"]
    out.append(f"| Pooled, seeds 46, 48, 49 | {f(cv['published'])} / {f(cv['lock'])} / {f(cv['forced'])} / {f(cv['lockroute'])} / {f(cv['route'])} | – | – | Δ {f(d['point'])} [{f(d['ci95'][0])}, {f(d['ci95'][1])}]: {d['reading']} |")
    out.append(f"clusters {c['delta_G_route_minus_forced']['n_clusters']}; published runs valid before/after s46 {f(W['s46']['published']['valid_before_rounding'])} {f(W['s46']['published']['valid_after_rounding'])}")
    out.append("lock before rounding s48 s49 " + f(W["s48"]["lock"]["valid_before_rounding"]) + " " + f(W["s49"]["lock"]["valid_before_rounding"]))
    out.append("lock patients valid before rounding s46: " + str(W["s46"]["lock"].get("patients_valid_before_rounding", W["s46"]["lock"].keys())))
    out.append("AUC range " + f(min(P[s]["model_info"]["test_auc"] for s in P)) + "–" + f(max(P[s]["model_info"]["test_auc"] for s in P)))
    out.append("p max " + f(max(P[s]["rules_descriptive"]["H4_rule"]["movability_null"]["p"] for s in P)))
    return out


base = O9 if (len(sys.argv) > 1 and sys.argv[1] == "v9") else O9 + "p5_v10/outputs/"
print("\n".join(rows(base)))
