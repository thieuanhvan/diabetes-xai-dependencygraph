"""Tables for P7 journal main_vi v4 (18/10/2026): Bảng F (DiCE genetic, now with BRFSS) and
Bảng G (exhaustive sparse search, tag _exh). Truncate to 4 decimals, Vietnamese decimal comma."""
import math
from pathlib import Path

import pandas as pd

C = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/outputs/crossdataset_p4")
OUT = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/outputs/journal_main/main_tables_vi_v3.md")
NAME = {"brfss2021": "BRFSS 2021", "nhis2022": "NHIS 2022", "nhis2024": "NHIS 2024",
        "nhanes2017-2020_diag": "NHANES 2017–2020, chẩn đoán", "nhanes2017-2020_a1c": "NHANES 2017–2020, HbA1c",
        "nhanes2021-2023_diag": "NHANES 2021–2023, chẩn đoán", "nhanes2021-2023_a1c": "NHANES 2021–2023, HbA1c"}


def t4(x):
    s = "−" if x < 0 else ""
    return s + f"{math.floor(abs(x) * 1e4) / 1e4:.4f}".replace(".", ",")


def pc(x):
    return f"{math.floor(x * 1e4) / 100:.2f}".replace(".", ",") + " %"


def ci(r):
    return f"{t4(r.est)} [{t4(r.ci_lo)}; {t4(r.ci_hi)}]"


L = []
gen = pd.read_csv(C / "cross_dataset_bootstrap_gen2.csv")
L.append("\n### Bảng F. DiCE genetic (cùng mô hình, cùng đoàn hệ), published và Δ validity khi thực thi\n")
L.append("| Bộ dữ liệu | n | Validity | CF chạm chỉ báo | CF không có cơ sở | CF không hành động được | Δ Bảng V [95 % CI] | Δ route A [95 % CI] |")
L.append("|---|---|---|---|---|---|---|---|")
for ds, nm in NAME.items():
    x = gen[gen.dataset == ds]
    if x.empty:
        continue
    lv = x[(x.contrast == "level") & (x["mode"] == "published")].set_index("metric").est
    d = x[x.contrast == "minus_published"].set_index("mode")
    L.append(f"| {nm} | {int(x.n_patients.iloc[0])} | {t4(lv['valid'])} | {pc(lv['touch'])} | {pc(lv['unsup'])} | "
             f"{pc(lv['fully'])} | {ci(d.loc['tableV'])} | {ci(d.loc['route_A'])} |")

exh = pd.read_csv(C / "cross_dataset_bootstrap_exh.csv")
L.append("\n### Bảng G. Tìm kiếm vét cạn (≤ 3 đặc trưng, tất định), published và Δ khoảng cách của CF tốt nhất khi thực thi\n")
L.append("| Bộ dữ liệu | n | CF chạm chỉ báo | CF không có cơ sở | CF không hành động được | Số thay đổi của CF tốt nhất | Khoảng cách của CF tốt nhất | Δ khoảng cách, Bảng V [95 % CI] | Δ khoảng cách, route A [95 % CI] |")
L.append("|---|---|---|---|---|---|---|---|---|")
for ds, nm in NAME.items():
    x = exh[exh.dataset == ds]
    if x.empty:
        continue
    lv = x[(x.contrast == "level") & (x["mode"] == "published")].set_index("metric").est
    d = x[(x.contrast == "minus_published") & (x.metric == "dist")].set_index("mode")
    L.append(f"| {nm} | {int(x.n_patients.iloc[0])} | {pc(lv['touch'])} | {pc(lv['unsup'])} | {pc(lv['fully'])} | "
             f"{t4(lv['n_changes'])} | {t4(lv['dist'])} | {ci(d.loc['tableV'])} | {ci(d.loc['route_A'])} |")
OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print(OUT.read_text(encoding="utf-8"))
