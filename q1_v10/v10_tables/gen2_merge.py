"""Merge the split gen2_brfss2021 run (19/11, queue_c2.sh): rows from the stopped queue a3 run plus one file per
remaining (seed, mode) pair (tag _gen2p_<seed>_<mode>) -> cross_brfss2021_gen2_{summary,changes}.csv in single-run
order (seeds 42, 123, 2024, 7, 31337; modes published, tableV, route_A). Originals go to gen2_split_backup/."""
import shutil
from pathlib import Path

import pandas as pd

R = Path(r"D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/outputs/crossdataset_p4/results")
B = R.parent / "gen2_split_backup"
B.mkdir(exist_ok=True)
SEEDS = [42, 123, 2024, 7, 31337]
MODES = ["published", "tableV", "route_A"]
for kind in ["summary", "changes"]:
    a = R / f"cross_brfss2021_gen2_{kind}.csv"
    shutil.copy2(a, B / a.name)
    parts = [pd.read_csv(a)]
    for f in sorted(R.glob(f"cross_brfss2021_gen2p_*_{kind}.csv")):
        shutil.copy2(f, B / f.name)
        parts.append(pd.read_csv(f))
    d = pd.concat(parts, ignore_index=True)
    d["_s"] = d.seed.map(SEEDS.index)
    d["_m"] = d["mode"].map(MODES.index)
    d = d.sort_values(["_s", "_m"], kind="stable").drop(columns=["_s", "_m"])
    if kind == "summary":
        pairs = list(zip(d.seed, d["mode"]))
        assert pairs == [(s, m) for s in SEEDS for m in MODES], pairs
        assert d.eligible.nunique() == 1 and d.auc.nunique() == 1 and d.cohort.nunique() == 1, "different model/cohort"
    d.to_csv(a, index=False)
    print(f"MERGED {kind}: {len(d)} rows from {len(parts)} files")
