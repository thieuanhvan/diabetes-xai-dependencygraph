"""Tables for P7 journal main_vi v2 (17/10/2026): NHIS from the _v2 random run, NHANES from the _v3 random run
(rebuilt NHANES files, 15/10), DiCE genetic from _gen2 (n_jobs -1, same models as the random runs).
Truncate to 4 decimals, Vietnamese decimal comma."""
import math
from pathlib import Path

import pandas as pd

C = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/outputs/crossdataset_p4")
OUT = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/outputs/journal_main/main_tables_vi_v2.md")
NAME = {"nhis2022": "NHIS 2022", "nhis2024": "NHIS 2024", "nhanes2017-2020_diag": "NHANES 2017–2020, chẩn đoán",
        "nhanes2017-2020_a1c": "NHANES 2017–2020, HbA1c", "nhanes2021-2023_diag": "NHANES 2021–2023, chẩn đoán",
        "nhanes2021-2023_a1c": "NHANES 2021–2023, HbA1c"}


def t4(x):
    s = "−" if x < 0 else ""
    return s + f"{math.floor(abs(x) * 1e4) / 1e4:.4f}".replace(".", ",")


def pc(x):
    return f"{math.floor(x * 1e4) / 100:.2f}".replace(".", ",") + " %"


rand = pd.concat([pd.read_csv(C / "cross_dataset_bootstrap.csv").query("dataset.str.startswith('nhis')"),
                  pd.read_csv(C / "cross_dataset_bootstrap_v3.csv")])
gen = pd.read_csv(C / "cross_dataset_bootstrap_gen2.csv")
L = []


def level_delta_table(b, title):
    L.append(f"\n### {title}\n")
    L.append("| Bộ dữ liệu | n | Validity | CF chạm chỉ báo | CF không có cơ sở | CF không hành động được | Δ Bảng V [95 % CI] | Δ route A [95 % CI] |")
    L.append("|---|---|---|---|---|---|---|---|")
    for ds, nm in NAME.items():
        x = b[b.dataset == ds]
        if x.empty:
            continue
        lv = x[(x.contrast == "level") & (x["mode"] == "published")].set_index("metric").est
        d = x[x.contrast == "minus_published"].set_index("mode")
        f = lambda m: f"{t4(d.loc[m, 'est'])} [{t4(d.loc[m, 'ci_lo'])}; {t4(d.loc[m, 'ci_hi'])}]"
        L.append(f"| {nm} | {int(x.n_patients.iloc[0])} | {t4(lv['valid'])} | {pc(lv['touch'])} | {pc(lv['unsup'])} | "
                 f"{pc(lv['fully'])} | {f('tableV')} | {f('route_A')} |")


level_delta_table(rand, "Bảng B′. DiCE random (pipeline gốc P4), published và Δ validity khi thực thi")
level_delta_table(gen, "Bảng F. DiCE genetic (cùng mô hình, cùng đoàn hệ), published và Δ validity khi thực thi")

diag = pd.read_csv(C / "nhis_diagnosis.csv").set_index("dataset")
L.append("\n### Bảng D′. Tỉ phần gain (dữ liệu hiện tại)\n")
L.append("| Bộ dữ liệu | Gain BMI | Gain các chỉ báo | Gain GenHlth |")
L.append("|---|---|---|---|")
for ds in ["brfss2021"] + list(NAME):
    if ds in diag.index:
        r = diag.loc[ds]
        L.append(f"| {NAME.get(ds, 'BRFSS 2021')} | {pc(r.gain_share_BMI)} | {pc(r.gain_share_indicators)} | {pc(r.gain_share_GenHlth)} |")

L.append("\n### Bảng E′. Tỉ lệ CF đổi BMI và validity theo nhóm (random; NHIS _v2, NHANES _v3)\n")
L.append("| Bộ dữ liệu | Chế độ | CF đổi BMI | Validity khi đổi BMI | Validity khi không đổi BMI |")
L.append("|---|---|---|---|---|")
for ds in ["nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c"]:
    tag = "_v2" if ds.startswith("nhis") else "_v3"
    x = pd.read_csv(C / f"results/cross_{ds}{tag}_changes.csv")
    x["bmi"] = x.changed.fillna("").str.contains("BMI")
    for mode in ["published", "tableV", "route_A"]:
        g = x[x["mode"] == mode]
        L.append(f"| {NAME[ds]} | {mode} | {pc(g.bmi.mean())} | {t4(g[g.bmi].valid.mean())} | {t4(g[~g.bmi].valid.mean())} |")
OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print(OUT.read_text(encoding="utf-8"))
