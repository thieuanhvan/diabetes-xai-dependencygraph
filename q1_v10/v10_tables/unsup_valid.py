import sys, math
import pandas as pd
sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
from depgraph.audit import classify
sys.stdout.reconfigure(encoding="utf-8")
for base in ("D:/20-study/uit/research/diabetesxai/paper7/outputs/crossdataset_p4/results/", "D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/outputs/crossdataset_p4/results/"):
    d = pd.read_csv(base + "cross_brfss2021_xgbrand_changes.csv")
    d = d[(d["mode"] == "published")]
    vcol = "valid" if "valid" in d.columns else None
    dv = d[d[vcol].astype(bool)] if vcol else d
    sets = [set(str(s).split(";")) - {"", "nan"} for s in dv.changed.fillna("")]
    cl = [classify(s, reading="narrow", rule="edge") for s in sets]
    dv = dv.assign(unsup=[r["unsupported"] for r in cl], touch=[r["touches_target"] for r in cl])
    pm = dv.groupby("pid")[["unsup", "touch"]].mean()
    t = lambda x: math.trunc(round(x * 10000, 6)) / 100
    print(base[-60:], len(dv), "patients", len(pm), "unsup", t(pm.unsup.mean()), "touch", t(pm.touch.mean()))
