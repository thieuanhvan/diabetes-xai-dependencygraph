"""Build the number tables for the P7 journal main_vi (truncate to 4 decimals, Vietnamese decimal comma)."""
import math
from pathlib import Path

import pandas as pd

H = Path("D:/20-study/uit/research/diabetesxai")
C = H / "paper7/outputs/crossdataset_p4"
P7 = Path("C:/Repos/uit/diabetes-xai-dependencygraph/outputs")
OUT = H / "paper7/outputs/journal_main/main_tables_vi.md"


def t4(x):
    """Truncate (not round) to 4 decimals, Vietnamese comma."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    s = "-" if x < 0 else ""
    v = math.floor(abs(x) * 10000) / 10000
    return s + f"{v:.4f}".replace(".", ",")


def pct(x):
    """Proportion -> percent with 2 decimals, truncated (0.123456 -> 12,34 %)."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    s = "-" if x < 0 else ""
    v = math.floor(abs(x) * 10000) / 100
    return s + f"{v:.2f}".replace(".", ",") + " %"


NAME = {"nhis2022": "NHIS 2022", "nhis2024": "NHIS 2024", "nhanes2017-2020_diag": "NHANES 2017–2020, nhãn chẩn đoán",
        "nhanes2017-2020_a1c": "NHANES 2017–2020, nhãn HbA1c", "nhanes2021-2023_diag": "NHANES 2021–2023, nhãn chẩn đoán",
        "nhanes2021-2023_a1c": "NHANES 2021–2023, nhãn HbA1c"}
ORDER = list(NAME)
lines = []

# Table A: BRFSS reference (P7 repo outputs)
ss = pd.read_csv(P7 / "seed_sweep.csv")
re_ = pd.read_csv(P7 / "route_enforcement.csv")
lines.append("### Bảng A. BRFSS 2021: số gốc của P7 (repo `diabetes-xai-dependencygraph`)\n")
lines.append("| Cấu hình | Validity (TB 5 seed) | CF chạm chỉ báo | CF không có cơ sở | CF không hành động được | Số vòng TB |")
lines.append("|---|---|---|---|---|---|")
for lab, g in re_.groupby("label"):
    n = g.n_cf.mean()
    lines.append(f"| {lab} | {t4(g.validity.mean())} | {pct(g.cf_touching_indicator.mean() / n)} | "
                 f"{pct(g.unsupported_edge_rule.mean() / n)} | {pct(g.fully_unactionable.mean() / n)} | {t4(g.rounds_mean.mean())} |")
lines.append(f"\nCột trong `seed_sweep.csv` (bản hội nghị, mô hình huấn luyện lại theo seed): {', '.join(ss.columns)}.\n")

# Table B: cross-dataset levels with bootstrap CI
bs = pd.read_csv(C / "cross_dataset_bootstrap.csv")
lv = bs[(bs.contrast == "level") & (bs["mode"] == "published")]
lines.append("### Bảng B. Lỗi của P7 trên NHIS và NHANES (pipeline gốc P4, bản published; trung bình theo bệnh nhân, [95 % CI bootstrap])\n")
lines.append("| Bộ dữ liệu | n bệnh nhân | Validity | CF chạm chỉ báo | CF không có cơ sở | CF không hành động được |")
lines.append("|---|---|---|---|---|---|")
for ds in ORDER:
    r = lv[lv.dataset == ds].set_index("metric")
    if r.empty:
        continue
    cell = lambda m, f: f"{f(r.loc[m, 'est'])} [{f(r.loc[m, 'ci_lo'])}; {f(r.loc[m, 'ci_hi'])}]"
    lines.append(f"| {NAME[ds]} | {int(r.n_patients.iloc[0])} | {cell('valid', t4)} | {cell('touch', pct)} | "
                 f"{cell('unsup', pct)} | {cell('fully', pct)} |")

# Table C: enforcement deltas
dl = bs[bs.contrast == "minus_published"]
lines.append("\n### Bảng C. Thay đổi validity khi thực thi so với published (điểm validity, [95 % CI bootstrap ghép cặp])\n")
lines.append("| Bộ dữ liệu | Bảng V (loại chỉ báo) | Thực thi theo tuyến (route A) |")
lines.append("|---|---|---|")
for ds in ORDER:
    r = dl[dl.dataset == ds].set_index("mode")
    if r.empty:
        continue
    cell = lambda m: f"{t4(r.loc[m, 'est'])} [{t4(r.loc[m, 'ci_lo'])}; {t4(r.loc[m, 'ci_hi'])}]"
    lines.append(f"| {NAME[ds]} | {cell('tableV')} | {cell('route_A')} |")

# Table D: NHIS mechanism
diag = pd.read_csv(C / "nhis_diagnosis.csv").set_index("dataset")
lines.append("\n### Bảng D. Cơ chế: tỉ phần độ quan trọng (total gain) của mô hình XGBoost\n")
lines.append("| Bộ dữ liệu | Gain của BMI | Gain của các chỉ báo | Gain của GenHlth | Đòn bẩy có trong dữ liệu |")
lines.append("|---|---|---|---|---|")
for ds in ["brfss2021"] + ORDER:
    if ds in diag.index:
        r = diag.loc[ds]
        lines.append(f"| {NAME.get(ds, 'BRFSS 2021')} | {pct(r.gain_share_BMI)} | {pct(r.gain_share_indicators)} | "
                     f"{pct(r.gain_share_GenHlth)} | {r.levers_present} |")
ch = []
for ds in ["nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c"]:
    d = pd.read_csv(C / f"results/cross_{ds}_v2_changes.csv")
    d["changed"] = d.changed.fillna("")
    d["bmi"] = d.changed.str.contains("BMI")
    for mode, g in d.groupby("mode"):
        ch.append({"ds": ds, "mode": mode, "share_bmi": g.bmi.mean(),
                   "valid_bmi": g[g.bmi].valid.mean(), "valid_nobmi": g[~g.bmi].valid.mean()})
ch = pd.DataFrame(ch)
lines.append("\n### Bảng E. Tỉ lệ CF có đổi BMI và validity theo nhóm (gộp 5 seed)\n")
lines.append("| Bộ dữ liệu | Chế độ | CF có đổi BMI | Validity khi đổi BMI | Validity khi không đổi BMI |")
lines.append("|---|---|---|---|---|")
for r in ch.itertuples():
    lines.append(f"| {NAME[r.ds]} | {r.mode} | {pct(r.share_bmi)} | {t4(r.valid_bmi)} | {t4(r.valid_nobmi)} |")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(OUT)
