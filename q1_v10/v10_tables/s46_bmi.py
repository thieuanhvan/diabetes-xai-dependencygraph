"""Table S46 columns 'CF changing BMI' (published -> lock) and validity with / without a BMI change under the lock,
DiCE random with XGBoost, pooled over returned counterfactuals. Reproduces the v9 printed values from the v9 files
before computing v10 (stops otherwise)."""
import math
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
O9 = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/crossdataset_p4/results")
O10 = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/outputs/crossdataset_p4/results")
DS = {"nhis2022": "_v2", "nhis2024": "_v2", "nhanes2017-2020_diag": "_v3", "nhanes2017-2020_a1c": "_v3",
      "nhanes2021-2023_diag": "_v3", "nhanes2021-2023_a1c": "_v3"}
V9 = {"nhanes2017-2020_diag": (0.4241, 0.6109, 0.9499, 0.6828), "nhis2022": (0.2073, 0.2473, 0.8383, 0.6888)}


def tr(x, k=4):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


def row(R, ds, t):
    d = pd.read_csv(R / f"cross_{ds}{t}_changes.csv").fillna({"changed": ""})
    bmi = d["changed"].str.split(";").apply(lambda s: "BMI" in s)
    pub, lock = d["mode"] == "published", d["mode"] == "tableV"
    return (bmi[pub].mean(), bmi[lock].mean(), d.loc[lock & bmi, "valid"].mean(), d.loc[lock & ~bmi, "valid"].mean())


for ds, v in V9.items():
    got = tuple(tr(x) for x in row(O9, ds, DS[ds]))
    if got != v:
        sys.exit(f"v9 not reproduced for {ds}: {got} vs {v}")
for ds, t in DS.items():
    print(ds, "v10", [tr(x) for x in row(O10, ds, t)])
