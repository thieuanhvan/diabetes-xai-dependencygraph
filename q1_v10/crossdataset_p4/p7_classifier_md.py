"""Markdown tables (truncated, not rounded) from classifier_robustness_{random,exh}.csv.

Usage: python p7_classifier_md.py <out.md>
Writes main Table 8 (four configurations) and Supplementary Tables S13 (DiCE random, all configurations)
and S14 (exhaustive search, all configurations).
"""
import math
import sys
from pathlib import Path

import pandas as pd

C = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4")
NAME = {"brfss2021": "BRFSS 2021", "nhis2022": "NHIS 2022", "nhis2024": "NHIS 2024",
        "nhanes2017-2020_diag": "NHANES 2017–2020, diagnosis", "nhanes2017-2020_a1c": "NHANES 2017–2020, HbA1c",
        "nhanes2021-2023_diag": "NHANES 2021–2023, diagnosis", "nhanes2021-2023_a1c": "NHANES 2021–2023, HbA1c"}
CLF = {"xgb": "XGBoost", "lr": "Logistic regression", "rf": "Random forest"}
MAIN = ["brfss2021", "nhis2022", "nhis2024", "nhanes2017-2020_diag"]


def tr(x, k):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


def f4(x):
    return f"{tr(x, 4):.4f}".replace("-", "−")


def pct(x):
    return f"{tr(x * 100, 2):.2f}%"


def ci(r, a):
    return f"{f4(r[a])} [{f4(r[a + '_lo'])}, {f4(r[a + '_hi'])}]"


def order(df):
    df = df.copy()
    df["o1"] = df.dataset.map(list(NAME).index)
    df["o2"] = df.clf.map(list(CLF).index)
    return df.sort_values(["o1", "o2"])


a = order(pd.read_csv(C / "classifier_robustness_random.csv"))
b = order(pd.read_csv(C / "classifier_robustness_exh.csv"))
L = []


def random_table(rows):
    L.append("| Survey | Classifier | AUC | n | Validity | Touch indicator | Unsupported | Fully unactionable | Δ indicator lock | Δ route-aware |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for _, r in rows.iterrows():
        if r.dataset == "brfss2021" and r.clf == "lr" and not ((rows.dataset == "brfss2021") & (rows.clf == "xgb")).any():
            # 11/11/2026 20:xx: used only while the shared-runner XGBoost BRFSS run (_xgbrand, five seeds) is missing
            # XGBoost BRFSS DiCE random comes from the conference runner (main Table 2): levels only, no paired contrasts
            L.append("| BRFSS 2021 | XGBoost | 0.8233 | 200 | 0.8130 | 32.24% | 21.36% | 10.42% | not run | see Table 2 |")
        L.append(f"| {NAME[r.dataset]} | {CLF[r.clf]} | {f4(r.auc)} | {int(r.cohort)} | {f4(r.pub_valid)} | {pct(r.pub_touch)} | "
                 f"{pct(r.pub_unsup)} | {pct(r.pub_fully)} | {ci(r, 'd_tableV')} | {ci(r, 'd_route_A')} |")


L.append("MAIN TABLE 8")
random_table(a[a.dataset.isin(MAIN)])
L.append("\nTABLE S13")
random_table(a)
L.append("\nTABLE S14")
L.append("| Survey | Classifier | n | Touch indicator | Unsupported | Fully unactionable | Changes, best CF | Distance, best CF | Δ distance, lock | Δ distance, route-aware |")
L.append("|---|---|---|---|---|---|---|---|---|---|")
for _, r in b.iterrows():
    L.append(f"| {NAME[r.dataset]} | {CLF[r.clf]} | {int(r.cohort)} | {pct(r.pub_touch)} | {pct(r.pub_unsup)} | {pct(r.pub_fully)} | "
             f"{f4(r.pub_n_changes)} | {f4(r.pub_dist)} | {ci(r, 'd_dist_tableV')} | {ci(r, 'd_dist_route_A')} |")
L.append("\nCHECKS")
L.append("random empty cells (lock, route): " + ", ".join(f"{r.clf}/{r.dataset}={int(r.empty_cells_tableV)}/{int(r.empty_cells_route_A)}" for _, r in a.iterrows()))
L.append("route-aware unsupported level max: " + f4(a.lvl_route_A_unsup.max()))
L.append("exh no-cf (lock, route): " + ", ".join(f"{r.clf}/{r.dataset}={int(r.no_cf_tableV)}/{int(r.no_cf_route_A)}" for _, r in b.iterrows()))
Path(sys.argv[1]).write_text("\n".join(L) + "\n", encoding="utf-8")
