"""Table S28 rows from ses_shares_and_runs.json. Usage: s28_rows.py [v9]"""
import json, math, sys
sys.stdout.reconfigure(encoding="utf-8")
O9 = "D:/20-study/uit/research/diabetesxai/paper7/outputs/"
def tr(x, k=4): return math.trunc(round(float(x) * 10 ** k, 6)) / 10 ** k
def f(x, k=4): return f"{tr(x, k):.{k}f}"
def pc(x): return f(float(x) * 100, 2) + "%"
base = O9 if (len(sys.argv) > 1 and sys.argv[1] == "v9") else O9 + "p5_v10/outputs/"
R = json.load(open(base + "q1_posthoc_ses_splits/ses_shares_and_runs.json", encoding="utf-8"))["posthoc_runs"]
for k, n in (("ses_freeze", "Socio-economic frozen (split 42)"), ("split_11", "Split 11"), ("split_22", "Split 22"), ("split_33", "Split 33"), ("split_44", "Split 44"), ("split_55", "Split 55")):
    r = R[k]
    print(f"| {n} | {f(r['O_share'])} vs {f(r['null'])} | {f(r['published_valid'])} / {f(r['lock_valid'])} | {pc(r['touch'])} | {pc(r['unsupported_kdigo'])} | {pc(r['single_nonindicator_flip'])} | {pc(r['O_A5_share_zero'])} | {f(r['kappa_ada_kdigo'])} |")
