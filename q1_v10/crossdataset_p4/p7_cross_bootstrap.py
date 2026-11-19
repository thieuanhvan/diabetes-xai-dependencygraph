"""Participant bootstrap for the cross-dataset P7 table (per-CF files written with --tag _v2).

Per patient (averaged over the 5 DiCE seeds and that patient's counterfactuals):
validity, share of CFs touching an indicator, share unsupported (edge rule), share fully
unactionable. Contrasts tableV - published and route_A - published are paired on patients
(the cohort is identical across modes). 2,000 resamples of patients; 95% percentile CIs.
Also checks that the v2 rerun reproduces the v1 per-seed summaries exactly.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

P7 = Path("C:/Repos/uit/diabetes-xai-dependencygraph")
sys.path.insert(0, str(P7 / "src"))
from depgraph.audit import classify  # noqa: E402

R = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4") / "results"
B = 2000
TAG = sys.argv[1] if len(sys.argv) > 1 else "_v2"  # "_v2" (DiCE random) or "_gen" (DiCE genetic)


def per_patient(df):
    sets = [set(str(s).split(";")) - {"", "nan"} for s in df.changed.fillna("")]
    cl = [classify(s, reading="narrow", rule="edge") for s in sets]
    df = df.assign(touch=[r["touches_target"] for r in cl], unsup=[r["unsupported"] for r in cl],
                   fully=[r["fully_unactionable"] for r in cl])
    return df.groupby(["mode", "pid"])[["valid", "touch", "unsup", "fully"]].mean()


rows, repro = [], []
for f in sorted(R.glob(f"cross_*{TAG}_changes.csv")):
    ds = f.name[len("cross_"):-len(f"{TAG}_changes.csv")]
    df = pd.read_csv(f)
    v1, v2 = R / f"cross_{ds}_summary.csv", R / f"cross_{ds}_v2_summary.csv"
    if TAG == "_v2" and v1.exists() and v2.exists():
        a = pd.read_csv(v1).set_index(["mode", "seed"])
        b = pd.read_csv(v2).set_index(["mode", "seed"])
        cols = ["n_cf", "validity", "cf_touching_indicator", "unsupported_edge_rule", "fully_unactionable"]
        repro.append({"dataset": ds, "identical_to_v1": bool((a[cols].round(10) == b.loc[a.index, cols].round(10)).all().all())})
    pp = per_patient(df)
    if not {"published", "tableV", "route_A"} <= set(pp.index.get_level_values("mode")):
        print(f"skip {ds}: not all modes finished"); continue
    pats = pp.loc["published"].index.to_numpy()
    rng = np.random.default_rng(20261015)
    idx = [rng.choice(len(pats), len(pats), replace=True) for _ in range(B)]
    for mode in ["published", "tableV", "route_A"]:
        m = pp.loc[mode].reindex(pats)
        for metric in ["valid", "touch", "unsup", "fully"]:
            x = m[metric].to_numpy()
            bs = np.array([np.nanmean(x[i]) for i in idx])
            rows.append({"dataset": ds, "mode": mode, "contrast": "level", "metric": metric, "n_patients": len(pats),
                         "est": np.nanmean(x), "ci_lo": np.quantile(bs, .025), "ci_hi": np.quantile(bs, .975)})
        if mode != "published":
            d = (m["valid"] - pp.loc["published"].reindex(pats)["valid"]).to_numpy()
            bs = np.array([np.nanmean(d[i]) for i in idx])
            rows.append({"dataset": ds, "mode": mode, "contrast": "minus_published", "metric": "valid",
                         "n_patients": len(pats), "est": np.nanmean(d), "ci_lo": np.quantile(bs, .025),
                         "ci_hi": np.quantile(bs, .975)})
out = pd.DataFrame(rows)
out.to_csv(R.parent / ("cross_dataset_bootstrap.csv" if TAG == "_v2" else f"cross_dataset_bootstrap{TAG}.csv"), index=False)
pd.set_option("display.width", 200)
print(pd.DataFrame(repro).to_string(index=False))
print(out[out.contrast == "minus_published"].round(4).to_string(index=False))
lv = out[(out.contrast == "level") & (out["mode"] == "published")].pivot(index="dataset", columns="metric", values="est")
print((lv * 100).round(1).to_string())
