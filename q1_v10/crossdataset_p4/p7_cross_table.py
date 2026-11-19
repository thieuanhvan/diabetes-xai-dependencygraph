"""Combine cross-dataset summaries into one table (means over seeds) + per-seed enforcement deltas."""
from pathlib import Path
import pandas as pd
R = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4") / "results"
rows = []
for f in sorted(R.glob("cross_*_summary.csv")):
    s = pd.read_csv(f)
    s["touch"] = s.cf_touching_indicator / s.n_cf * 100
    s["unsup"] = s.unsupported_edge_rule / s.n_cf * 100
    s["fully"] = s.fully_unactionable / s.n_cf * 100
    pv = s.pivot(index="seed", columns="mode", values="validity")
    for mode, g in s.groupby("mode"):
        r = {"dataset": g.dataset.iloc[0], "mode": mode, "seeds": len(g), "AUC": g.auc.iloc[0],
             "cohort": int(g.cohort.iloc[0]), "validity": g.validity.mean(), "touch%": g.touch.mean(),
             "unsup%": g.unsup.mean(), "fully%": g.fully.mean(), "rounds": g.rounds_mean.mean(),
             "no_cf": g.queries_with_no_cf.sum()}
        if mode != "published":
            d = pv[mode] - pv["published"]
            r["dValidity"] = d.mean(); r["seeds_up"] = int((d > 0).sum()); r["seeds_down"] = int((d < 0).sum())
        rows.append(r)
t = pd.DataFrame(rows)
order = {"published": 0, "tableV": 1, "route_A": 2}
t = t.sort_values(["dataset", "mode"], key=lambda c: c.map(order) if c.name == "mode" else c)
pd.set_option("display.width", 200)
print(t.round(3).to_string(index=False))
t.round(4).to_csv(R.parent / "cross_dataset_table.csv", index=False)
