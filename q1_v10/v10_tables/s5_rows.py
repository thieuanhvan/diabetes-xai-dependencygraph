"""s5_rows.py <crossdataset_p4 folder>: Supplementary Table S5 (both parts), truncated.
Part 1 from cross_menthlth_sensitivity.csv (p7_menthlth_sensitivity.py; pooled over counterfactuals, ranges over the
six NHIS and NHANES configurations); part 2 from cross_dataset_bootstrap_exh.csv rows <ds> (integer grid) and
<ds>_mh (observed codes). Run on the v9 folder first to check against the printed v9 table."""
import math
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
C = Path(sys.argv[1])


def tr(x, k=4):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


def p(x):
    return f"{tr(x * 100, 2):.2f}"


def f(x):
    s = f"{tr(x):.4f}".replace("-", "−")
    return s if s.startswith("−") else "+" + s


m = pd.read_csv(C / "cross_menthlth_sensitivity.csv")
m = m[m.config.isin(["nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c", "nhanes2021-2023_diag", "nhanes2021-2023_a1c"])]  # XGBoost only
print("PART 1")
gens = ["DiCE random", "DiCE genetic", "exhaustive"]
for g in gens:
    d = m[m.generator == g]
    cells = []
    for c in ["change_MentHlth", "touch_indicator", "touch_GenHlth_or_PhysHlth", "MentHlth_only_indicator"]:
        cells.append(f"{p(d[c].min())}–{p(d[c].max())}%")
    nm = "Exhaustive search" if g == "exhaustive" else g
    print(f"| {nm} | " + " | ".join(cells) + f" |   <!-- n configs {len(d)} -->")
print("touch drop range (touch - GenHlth):", p((m.touch_indicator - m.touch_GenHlth_or_PhysHlth).min()),
      p((m.touch_indicator - m.touch_GenHlth_or_PhysHlth).max()), " GenHlth range all gens:",
      p(m.touch_GenHlth_or_PhysHlth.min()), p(m.touch_GenHlth_or_PhysHlth.max()))
b = pd.read_csv(C / "cross_dataset_bootstrap_exh.csv")
NAME = {"nhis2022": "NHIS 2022", "nhis2024": "NHIS 2024",
        "nhanes2017-2020_diag": "NHANES 2017–2020, diagnosis", "nhanes2017-2020_a1c": "NHANES 2017–2020, HbA1c",
        "nhanes2021-2023_diag": "NHANES 2021–2023, diagnosis", "nhanes2021-2023_a1c": "NHANES 2021–2023, HbA1c"}
print("PART 2")
mx = {"touch": 0, "unsup": 0}
for ds, nm in NAME.items():
    vals = {}
    for key, lab in ((ds, "integer 0–30"), (ds + "_mh", "observed codes")):
        d = b[b.dataset == key]
        if not len(d):
            print("MISSING", key)
            continue
        g = lambda mo, c, met: d[(d["mode"] == mo) & (d.contrast == c) & (d.metric == met)].iloc[0]  # noqa: E731
        lv = {k: g("published", "level", k).est for k in ("touch", "unsup", "fully")}
        vals[lab] = lv
        r = g("route_A", "minus_published", "dist")
        nc = g("route_A", "minus_published", "n_changes").est
        print(f"| {nm} | {lab} | {p(lv['touch'])}% | {p(lv['unsup'])}% | {p(lv['fully'])}% | {f(r.est)} [{tr(r.ci_lo):.4f}, {tr(r.ci_hi):.4f}] |"
              f"   <!-- route d n_changes {nc:+.4f}; ci_lo>0 {r.ci_lo > 0} -->")
    if len(vals) == 2:
        for k in mx:
            mx[k] = max(mx[k], abs(vals["integer 0–30"][k] - vals["observed codes"][k]))
print("max change touch/unsup (points):", p(mx["touch"]), p(mx["unsup"]))
