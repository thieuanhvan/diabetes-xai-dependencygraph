"""Table S17 rows from cross_dataset_bootstrap_exh.csv (v9 check against the printed BRFSS row, then v10)."""
import math
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
NAME = {"brfss2021": "BRFSS 2021", "nhis2022": "NHIS 2022", "nhis2024": "NHIS 2024",
        "nhanes2017-2020_diag": "NHANES 2017–2020, diagnosis", "nhanes2017-2020_a1c": "NHANES 2017–2020, HbA1c",
        "nhanes2021-2023_diag": "NHANES 2021–2023, diagnosis", "nhanes2021-2023_a1c": "NHANES 2021–2023, HbA1c"}


def tr(x, k=4):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


def f(x):
    return f"{tr(x):.4f}".replace("-", "−")


def p(x):
    return f"{tr(x * 100, 2):.2f}%"


def rows(path):
    t = pd.read_csv(path)
    out = []
    for ds, nm in NAME.items():
        d = t[t.dataset == ds]
        g = lambda m, c, met: d[(d["mode"] == m) & (d.contrast == c) & (d.metric == met)].iloc[0]  # noqa: E731
        lv = lambda met: g("published", "level", met).est  # noqa: E731
        dl, dr = g("tableV", "minus_published", "dist"), g("route_A", "minus_published", "dist")
        n = int(g("published", "level", "touch").n_patients)
        out.append(f"| {nm} | {n} | {p(lv('touch'))} | {p(lv('unsup'))} | {p(lv('fully'))} | {f(lv('n_changes'))} | {f(lv('dist'))} | "
                   f"{f(dl.est)} [{f(dl.ci_lo)}, {f(dl.ci_hi)}] | {f(dr.est)} [{f(dr.ci_lo)}, {f(dr.ci_hi)}] |")
    return out


v9 = rows("D:/20-study/uit/research/diabetesxai/paper7/outputs/crossdataset_p4/cross_dataset_bootstrap_exh.csv")
assert v9[0] == "| BRFSS 2021 | 200 | 54.40% | 36.50% | 25.00% | 1.0650 | 0.9198 | 0.0665 [0.0381, 0.0989] | 0.0570 [0.0298, 0.0875] |", v9[0]
print("\n".join(rows("D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/outputs/crossdataset_p4/cross_dataset_bootstrap_exh.csv")))
