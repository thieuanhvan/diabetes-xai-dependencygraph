"""Coverage and yield of DiCE random (tag _v2) on NHIS/NHANES, per configuration and mode, from stored outputs.
requested = cohort x 5 seeds x 5 counterfactuals; returned = rows in the changes file; patient-seed coverage = share of
(patient, seed) cells with at least one counterfactual; supported = valid and not unsupported under the primary
edge rule; yield = valid supported counterfactuals per 5 requested, averaged over patient-seed cells."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
from depgraph.audit import classify  # noqa: E402

R = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4") / "results"
rows = []
TAG = sys.argv[1] if len(sys.argv) > 1 else "_v2"
for f in sorted(R.glob(f"cross_*{TAG}_changes.csv")):
    ds = f.name[len("cross_"):-len(f"{TAG}_changes.csv")]
    if "bmi4" in ds:
        continue
    d = pd.read_csv(f)
    s = pd.read_csv(R / f"cross_{ds}{TAG}_summary.csv")
    sets = [set(str(x).split(";")) - {"", "nan"} for x in d.changed.fillna("")]
    d = d.assign(sup=[(v == 1) and not classify(c, reading="narrow", rule="edge")["unsupported"] for v, c in zip(d.valid, sets)])
    for mode in ["published", "tableV", "route_A"]:
        m = d[d["mode"] == mode]
        sm = s[s["mode"] == mode]
        cohort, seeds = int(sm.cohort.iloc[0]), sm.seed.nunique()
        cells = cohort * seeds
        per = m.groupby(["pid", "seed"]).agg(n=("sup", "size"), k=("sup", "sum"))
        rows.append({"config": ds, "mode": mode, "requested": cells * 5, "returned": len(m),
                     "returned_share": len(m) / (cells * 5), "cell_coverage": len(per) / cells,
                     "cell_with_valid_supported": (per.k > 0).sum() / cells,
                     "yield_per_5": per.k.sum() / cells / 5})
t = pd.DataFrame(rows)
t.to_csv(R.parent / f"cross_coverage_yield{TAG}.csv", index=False)
pd.set_option("display.width", 200)
print(t.round(4).to_string(index=False))
