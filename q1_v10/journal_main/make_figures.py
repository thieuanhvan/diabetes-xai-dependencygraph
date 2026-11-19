"""Figures for the P7 journal version (matplotlib only; reproducible from the result CSVs).

Fig 2: change in validity under enforcement vs published, per dataset (paired bootstrap 95% CI).
Fig 3: share of counterfactuals that change BMI, per mode, and validity of BMI vs non-BMI CFs.
Figure 1 (dependency graph) already exists in the P7 repo (analysis/make_fig1_kg.py).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

H = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/outputs")
C = H / "crossdataset_p4"
OUT = H / "journal_main" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "pdf.fonttype": 42,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, ORANGE, GRID, INK = "#2a78d6", "#eb6834", "#d9d9d6", "#2b2b2b"
NAME = {"nhis2022": "NHIS 2022", "nhis2024": "NHIS 2024",
        "nhanes2017-2020_diag": "NHANES 2017-20, diagnosis", "nhanes2017-2020_a1c": "NHANES 2017-20, HbA1c",
        "nhanes2021-2023_diag": "NHANES 2021-23, diagnosis", "nhanes2021-2023_a1c": "NHANES 2021-23, HbA1c"}
ORDER = list(NAME)
SHORT = {"nhis2022": "NHIS\n2022", "nhis2024": "NHIS\n2024", "nhanes2017-2020_diag": "NHANES\n2017-20\ndiagnosis", "nhanes2017-2020_a1c": "NHANES\n2017-20\nHbA1c"}

# ---- Fig 2: forest plot of validity change -----------------------------------------
# NHIS from the _v2 random run, NHANES from the _v3 random run (NHANES files rebuilt 15/10)
bs = pd.concat([pd.read_csv(C / "cross_dataset_bootstrap.csv").query("dataset.str.startswith('nhis')"),
                pd.read_csv(C / "cross_dataset_bootstrap_v3.csv")])
d = bs[bs.contrast == "minus_published"]
fig, ax = plt.subplots(figsize=(6.4, 3.4))
ys = range(len(ORDER))
for off, mode, col, lab in ((-0.15, "tableV", BLUE, "Indicator lock"),
                            (0.15, "route_A", ORANGE, "Route-aware enforcement")):
    r = d[d["mode"] == mode].set_index("dataset").reindex(ORDER)
    y = [i + off for i in ys]
    ax.hlines(y, r.ci_lo, r.ci_hi, color=col, lw=2)
    ax.plot(r.est, y, "o", color=col, ms=6, mec="white", mew=1.5, label=lab)
ax.axvline(0, color=INK, lw=0.8)
ax.set_yticks(list(ys))
ax.set_yticklabels([NAME[k] for k in ORDER])
ax.invert_yaxis()
ax.set_xlabel("Change in validity vs. published (95% CI, patient bootstrap)")
ax.xaxis.grid(True, color=GRID, lw=0.6)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=8)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(OUT / f"fig2_validity_cost.{ext}", dpi=300)
plt.close(fig)

# ---- Fig 3: BMI routing ----------------------------------------------------------
rows = []
for ds in ["nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c"]:
    x = pd.read_csv(C / f"results/cross_{ds}{'_v2' if ds.startswith('nhis') else '_v3'}_changes.csv")
    x["bmi"] = x.changed.fillna("").str.contains("BMI")
    for mode, g in x.groupby("mode"):
        rows.append({"ds": ds, "mode": mode, "share": g.bmi.mean(),
                     "v_bmi": g[g.bmi].valid.mean(), "v_no": g[~g.bmi].valid.mean()})
t = pd.DataFrame(rows)
modes = ["published", "tableV", "route_A"]
mlab = {"published": "Published", "tableV": "Indicator lock", "route_A": "Route-aware"}
dss = ["nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c"]
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.3))
w = 0.26
for j, mode in enumerate(modes):
    r = t[t["mode"] == mode].set_index("ds").reindex(dss)
    shade = {0: "#9ec5f4", 1: BLUE, 2: "#184f95"}[j]
    axes[0].bar([i + (j - 1) * w for i in range(len(dss))], r.share * 100, width=w - 0.02,
                color=shade, label=mlab[mode])
axes[0].set_xticks(range(len(dss)))
axes[0].set_xticklabels([SHORT[k] for k in dss], fontsize=7.5)
axes[0].set_ylabel("Counterfactuals that change BMI (%)")
axes[0].yaxis.grid(True, color=GRID, lw=0.6)
axes[0].set_axisbelow(True)
axes[0].legend(frameon=False, fontsize=7.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
r = t[t["mode"] == "tableV"].set_index("ds").reindex(dss)
axes[1].bar([i - 0.18 for i in range(len(dss))], r.v_bmi, width=0.34, color=BLUE, label="CF changes BMI")
axes[1].bar([i + 0.18 for i in range(len(dss))], r.v_no, width=0.34, color=ORANGE, label="CF does not change BMI")
axes[1].set_xticks(range(len(dss)))
axes[1].set_xticklabels([SHORT[k] for k in dss], fontsize=7.5)
axes[1].set_ylim(0, 1.0)
axes[1].set_ylabel("Validity under indicator lock")
axes[1].yaxis.grid(True, color=GRID, lw=0.6)
axes[1].set_axisbelow(True)
axes[1].legend(frameon=False, fontsize=7.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(OUT / f"fig3_bmi_routing.{ext}", dpi=300)
plt.close(fig)
print("written:", sorted(p.name for p in OUT.iterdir()))
