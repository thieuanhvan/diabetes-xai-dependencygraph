"""s1314_rows.py <folder with classifier_robustness_{random,exh}.csv>: rows of Supplementary Tables S13 (DiCE random)
and S14 (exhaustive search) for all classifiers, truncated (guarded as in gen_rows.py).
Run on the v9 folder first to check against the printed v9 tables, then on the v10 folder."""
import math
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
C = Path(sys.argv[1])
NAME = {"brfss2021": "BRFSS 2021", "nhis2022": "NHIS 2022", "nhis2024": "NHIS 2024",
        "nhanes2017-2020_diag": "NHANES 2017–2020, diagnosis", "nhanes2017-2020_a1c": "NHANES 2017–2020, HbA1c",
        "nhanes2021-2023_diag": "NHANES 2021–2023, diagnosis", "nhanes2021-2023_a1c": "NHANES 2021–2023, HbA1c"}
CLF = {"xgb": "XGBoost", "lr": "Logistic regression", "rf": "Random forest"}


def tr(x, k=4):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


def f(x):
    return f"{tr(x):.4f}".replace("-", "−")


def p(x):
    return f"{tr(x * 100, 2):.2f}%"


def ci(e, lo, hi):
    return f"{f(e)} [{f(lo)}, {f(hi)}]"


r = pd.read_csv(C / "classifier_robustness_random.csv")
e = pd.read_csv(C / "classifier_robustness_exh.csv")
print("S13")
for ds, nm in NAME.items():
    for c, cn in CLF.items():
        x = r[(r.dataset == ds) & (r.clf == c)]
        if not len(x):
            print("MISSING", c, ds)
            continue
        x = x.iloc[0]
        print(f"| {nm} | {cn} | {f(x.auc)} | {int(x.cohort)} | {f(x.pub_valid)} | {p(x.pub_touch)} | {p(x.pub_unsup)} | "
              f"{p(x.pub_fully)} | {ci(x.d_tableV, x.d_tableV_lo, x.d_tableV_hi)} | "
              f"{ci(x.d_route_A, x.d_route_A_lo, x.d_route_A_hi)} |")
print("S14")
nocf = 0
for ds, nm in NAME.items():
    for c, cn in CLF.items():
        x = e[(e.dataset == ds) & (e.clf == c)]
        if not len(x):
            print("MISSING", c, ds)
            continue
        x = x.iloc[0]
        nocf += int(x.no_cf_tableV) + int(x.no_cf_route_A)
        print(f"| {nm} | {cn} | {int(x.cohort)} | {p(x.pub_touch)} | {p(x.pub_unsup)} | {p(x.pub_fully)} | "
              f"{f(x.pub_n_changes)} | {f(x.pub_dist)} | {ci(x.d_dist_tableV, x.d_dist_tableV_lo, x.d_dist_tableV_hi)} | "
              f"{ci(x.d_dist_route_A, x.d_dist_route_A_lo, x.d_dist_route_A_hi)} |")
print("patients without a counterfactual (lock + route, all rows):", nocf)
xe = e[e.clf == "xgb"]
print("XGB exhaustive fully range:", p(xe.pub_fully.min()), p(xe.pub_fully.max()))
