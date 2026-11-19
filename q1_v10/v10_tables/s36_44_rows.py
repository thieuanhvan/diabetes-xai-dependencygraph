"""Tables S36 and S44 rows + S-P5 prose numbers from forced_lever_levers_only.json. Usage: s36_44_rows.py [v9]"""
import json
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")
O9 = "D:/20-study/uit/research/diabetesxai/paper7/outputs/"


def tr(x, k=4):
    return math.trunc(round(float(x) * 10 ** k, 6)) / 10 ** k


def f(x, k=4):
    return f"{tr(x, k):.{k}f}".replace("-", "−")


def pc(x):
    return f(float(x) * 100, 2) + "%"


base = O9 if (len(sys.argv) > 1 and sys.argv[1] == "v9") else O9 + "p5_v10/outputs/"
d = json.load(open(base + "q1_posthoc_v5/analysis/forced_lever_levers_only.json", encoding="utf-8"))
W = d["wachter"]
names = (("s44", "Seed 44"), ("s45", "Seed 45"), ("s46", "Seed 46"), ("s48", "Seed 48"), ("s49", "Seed 49"), ("lr", "LR"))
print("S36")
for k, n in names:
    L = W[k]["levers"]
    r5 = L["kept_r5"]
    print(f"| {n} | {L['coverage_x']}; {L['action_coverage_r5_x']} | {f(L['valid_before_rounding'])} / {f(L['valid_after_rounding'])} | {L['kept_outputs']}; {pc(r5['changes_highbp_or_highchol'])}; {pc(r5['no_action_r5'])} | {pc(W[k]['forced']['kept_r5']['no_action_r5'])} | {pc(W[k]['route']['kept_r5']['no_action_r5'])} |")
print("indicator touch in levers kept (all nets):", [W[k]["levers"]["kept_v4"]["touch_indicator"] for k, _ in names])
print("indicator touch in forced kept:", [W[k]["forced"]["kept_v4"]["touch_indicator"] for k, _ in names])
print("forced kept with HighBP/HighChol forced 46/48/49:", [W[k]["forced"].get("kept_with_highbp_or_highchol_forced") for k in ("s46", "s48", "s49")])
print("lock valid before rounding 46/48/49:", [f(W[k]["lock"]["valid_before_rounding"]) for k in ("s46", "s48", "s49")])
print("j1 equals lock:", [W[k]["levers"]["j1_equals_lock_share"] for k, _ in names])
print("cpu hours levers:", f(sum(W[k]["levers"]["cpu_hours"] for k, _ in names), 2))
print("S44")
for k, n in names:
    w = W[k]
    cov = " / ".join(str(w[m]["coverage_x"]) for m in ("published", "lock", "forced", "levers", "lockroute", "route"))
    ac = " / ".join(str(w[m]["action_coverage_r5_x"]) for m in ("forced", "levers", "route"))
    print(f"| {n} | {cov} | {ac} | {f(w['delta_route_minus_levers'])} | {f(w['delta_route_minus_forced'])} |")
for key in ("key_seeds_46_48_49", "all_accepted_seeds"):
    p = d["pooled"][key]
    c, a = p["coverage"], p["action_coverage_r5"]
    dl, dg = p["delta_L_route_minus_levers"], p["delta_G_route_minus_forced_S_P4"]
    print(key, "| " + " / ".join(f(c[m]) for m in ("published", "lock", "forced", "levers", "lockroute", "route")) + " | " + " / ".join(f(a[m]) for m in ("forced", "levers", "route")) + f" | {f(dl['point'])} [{f(dl['ci95'][0])}, {f(dl['ci95'][1])}] | {f(dg['point'])} [{f(dg['ci95'][0])}, {f(dg['ci95'][1])}] |", dl["reading"], "|", dg["reading"], "clusters", dl["n_clusters"])
    if "delta_action_coverage_route_minus_levers" in p:
        q = p["delta_action_coverage_route_minus_levers"]
        print("  action Δ", f(q["point"]), f(q["ci95"][0]), f(q["ci95"][1]))
