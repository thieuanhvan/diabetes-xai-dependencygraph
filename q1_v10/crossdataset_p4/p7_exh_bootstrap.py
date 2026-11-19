"""Participant bootstrap for the exhaustive-search generator (tag _exh).

Per patient: share of its CFs touching an indicator / unsupported (edge rule) / fully unactionable,
number of changes and distance of its best CF. Contrasts tableV - published and route_A - published
on the best-CF distance and number of changes, paired on patients. 2,000 resamples, 95% percentile CIs.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
from depgraph.audit import classify  # noqa: E402

R = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4") / "results"
B = 2000
rows = []
for f in sorted(R.glob("cross_*_exh_changes.csv")):
    ds = f.name[len("cross_"):-len("_exh_changes.csv")]
    df = pd.read_csv(f)
    sets = [set(str(s).split(";")) - {"", "nan"} for s in df.changed.fillna("")]
    cl = [classify(s, reading="narrow", rule="edge") for s in sets]
    df = df.assign(touch=[r["touches_target"] for r in cl], unsup=[r["unsupported"] for r in cl],
                   fully=[r["fully_unactionable"] for r in cl])
    share = df.groupby(["mode", "pid"])[["touch", "unsup", "fully"]].mean()
    best = df.sort_values(["n_changes", "dist"]).groupby(["mode", "pid"]).first()[["n_changes", "dist"]]
    pp = share.join(best)
    pats = pp.loc["published"].index.to_numpy()
    rng = np.random.default_rng(20261018)
    idx = [rng.choice(len(pats), len(pats), replace=True) for _ in range(B)]
    for mode in ["published", "tableV", "route_A"]:
        m = pp.loc[mode].reindex(pats)
        for metric in ["touch", "unsup", "fully", "n_changes", "dist"]:
            x = m[metric].to_numpy()
            bs = np.array([np.nanmean(x[i]) for i in idx])
            rows.append({"dataset": ds, "mode": mode, "contrast": "level", "metric": metric, "n_patients": len(pats),
                         "est": np.nanmean(x), "ci_lo": np.quantile(bs, .025), "ci_hi": np.quantile(bs, .975)})
        if mode != "published":
            for metric in ["n_changes", "dist"]:
                d = (m[metric] - pp.loc["published"].reindex(pats)[metric]).to_numpy()
                bs = np.array([np.nanmean(d[i]) for i in idx])
                rows.append({"dataset": ds, "mode": mode, "contrast": "minus_published", "metric": metric,
                             "n_patients": len(pats), "est": np.nanmean(d), "ci_lo": np.quantile(bs, .025),
                             "ci_hi": np.quantile(bs, .975)})
out = pd.DataFrame(rows)
out.to_csv(R.parent / "cross_dataset_bootstrap_exh.csv", index=False)
pd.set_option("display.width", 200)
print(out[out.contrast == "minus_published"].round(4).to_string(index=False))
lv = out[(out.contrast == "level") & (out["mode"] == "published")].pivot(index="dataset", columns="metric", values="est")
print(lv.round(4).to_string())
