"""gen_rows.py <crossdataset_p4 folder>: rows of Supplementary Table S11 (coverage and yield, DiCE random NHIS/NHANES
and DiCE genetic) and Table S16 (DiCE genetic), truncated, plus the touch range for main Section 4.6.
Run on the v9 folder to confirm it reproduces the printed v9 tables, then on the v10 folder."""
import math
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
C = Path(sys.argv[1])
NAME = {"brfss2021": "BRFSS 2021", "nhis2022": "NHIS 2022", "nhis2024": "NHIS 2024",
        "nhanes2017-2020_diag": "NHANES 2017–2020, diagnosis", "nhanes2017-2020_a1c": "NHANES 2017–2020, HbA1c",
        "nhanes2021-2023_diag": "NHANES 2021–2023, diagnosis", "nhanes2021-2023_a1c": "NHANES 2021–2023, HbA1c"}
MODE = {"published": "published", "tableV": "indicator lock", "route_A": "route-aware"}


def tr(x, k=4):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


def f(x):
    return f"{tr(x):.4f}".replace("-", "−")


def p(x):
    return f"{tr(x * 100, 2):.2f}%"


cy = pd.concat([pd.read_csv(C / "cross_coverage_yield_v2.csv"), pd.read_csv(C / "cross_coverage_yield_v3.csv")])
g2 = pd.read_csv(C / "cross_coverage_yield_gen2.csv")
s11 = []
for gen, t in (("DiCE random", cy), ("DiCE genetic", g2)):
    for ds, nm in NAME.items():
        for m, mn in MODE.items():
            r = t[(t.config == ds) & (t["mode"] == m)]
            if not len(r):
                continue
            r = r.iloc[0]
            s11.append(f"| {gen} | {nm} | {mn} | {int(r.returned)}/{int(r.requested)} | {p(r.cell_coverage)} | "
                       f"{p(r.cell_with_valid_supported)} | {f(r.yield_per_5)} |")
b = pd.read_csv(C / "cross_dataset_bootstrap_gen2.csv")
s16, touch = [], []
for ds, nm in NAME.items():
    d = b[b.dataset == ds]
    if not len(d):
        s16.append(f"MISSING {ds}")
        continue
    g = lambda m, c, met: d[(d["mode"] == m) & (d.contrast == c) & (d.metric == met)].iloc[0]  # noqa: E731
    lv = lambda met: g("published", "level", met).est  # noqa: E731
    dl, dr = g("tableV", "minus_published", "valid"), g("route_A", "minus_published", "valid")
    touch.append(lv("touch"))
    s16.append(f"| {nm} | {int(g('published', 'level', 'touch').n_patients)} | {f(lv('valid'))} | {p(lv('touch'))} | {p(lv('unsup'))} | "
               f"{p(lv('fully'))} | {f(dl.est)} [{f(dl.ci_lo)}, {f(dl.ci_hi)}] | {f(dr.est)} [{f(dr.ci_lo)}, {f(dr.ci_hi)}] |"
               f" <!-- route n {int(dr.n_patients)} -->")
print("S11")
print("\n".join(s11))
print("S16")
print("\n".join(s16))
print("TOUCH RANGE", p(min(touch)), p(max(touch)))
