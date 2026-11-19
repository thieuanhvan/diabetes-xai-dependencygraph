"""P7 round-4 check: does the indicator failure depend on the MentHlth proxy (NHIS DEPFREQ_A, NHANES PHQ-9 bands)?
From stored outputs (published mode): share of counterfactuals that change MentHlth, share that touch an indicator,
and share that touch an indicator other than MentHlth (GenHlth or PhysHlth). Pooled over seeds and patients."""
import sys
from pathlib import Path

import pandas as pd

R = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4\results")
OUT = Path(sys.argv[1])
IND = {"GenHlth", "PhysHlth", "MentHlth"}
rows = []
# final DiCE random runs: _v3 for NHANES (main Table 3), _v2 for NHIS (no _v3)
for tag, gen in (("_v3", "DiCE random"), ("_v2", "DiCE random"), ("_gen2", "DiCE genetic"), ("_exh", "exhaustive")):
    for f in sorted(R.glob(f"cross_*{tag}_changes.csv")):
        ds = f.name[len("cross_"):-len(f"{tag}_changes.csv")]
        if "bmi4" in ds or "nosmk" in ds or "_mh" in ds or ds.startswith("brfss"):
            continue
        if gen == "DiCE random" and ds.startswith("nhanes") != (tag == "_v3"):
            continue
        d = pd.read_csv(f)
        d = d[d["mode"] == "published"]
        sets = [set(str(s).split(";")) - {"", "nan"} for s in d["changed"].fillna("")]
        n = len(sets)
        ment = sum("MentHlth" in s for s in sets)
        touch = sum(bool(s & IND) for s in sets)
        other = sum(bool(s & (IND - {"MentHlth"})) for s in sets)
        only_ment = sum(("MentHlth" in s) and not (s & (IND - {"MentHlth"})) for s in sets)
        rows.append({"generator": gen, "config": ds, "n_cf": n, "change_MentHlth": ment / n, "touch_indicator": touch / n,
                     "touch_GenHlth_or_PhysHlth": other / n, "MentHlth_only_indicator": only_ment / n})
t = pd.DataFrame(rows)
t.to_csv(OUT, index=False)
pd.set_option("display.width", 200)
print(t.round(4).to_string(index=False))
print("\nranges by generator:")
print(t.groupby("generator")[["change_MentHlth", "touch_indicator", "touch_GenHlth_or_PhysHlth", "MentHlth_only_indicator"]].agg(["min", "max"]).round(4).to_string())
