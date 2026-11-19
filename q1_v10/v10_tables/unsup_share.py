"""Share of indicator-touching DiCE random counterfactuals (published mode, XGBoost) with no supporting edge, NHIS and
NHANES (main text 4.3), pooled over counterfactuals and as a ratio of patient means; v9 and v10."""
import math
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
from depgraph.audit import classify  # noqa: E402

O = {"v9": Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/crossdataset_p4/results"),
     "v10": Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/outputs/crossdataset_p4/results")}
DS = {"nhis2022": "_v2", "nhis2024": "_v2", "nhanes2017-2020_diag": "_v3", "nhanes2017-2020_a1c": "_v3",
      "nhanes2021-2023_diag": "_v3", "nhanes2021-2023_a1c": "_v3", "brfss2021": "_xgbrand"}


def tr(x, k=4):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


for v, R in O.items():
    for ds, t in DS.items():
        d = pd.read_csv(R / f"cross_{ds}{t}_changes.csv").fillna({"changed": ""})
        d = d[d["mode"] == "published"]
        cl = [classify(set(str(s).split(";")) - {"", "nan"}, reading="narrow", rule="edge") for s in d.changed]
        touch = pd.Series([c["touches_target"] for c in cl], index=d.index)
        uns = pd.Series([c["unsupported"] for c in cl], index=d.index)
        pooled = uns[touch].mean()
        pm = d.assign(t=touch, u=uns).groupby("pid")[["t", "u"]].mean()
        print(v, ds, "pooled", tr(pooled), "ratio_of_means", tr(pm.u.mean() / pm.t.mean()))
