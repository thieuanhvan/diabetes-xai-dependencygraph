"""Interim (no file written): R5 rows of the DiCE / exhaustive diabetes runs available now, via v5_reclass.cross_block()
of the shadow tools. The full v5_reclass run (all generators) is repeated once the BRFSS post-hoc runs exist."""
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent / "tools_v10" / "q1_posthoc_v5"))
import pandas as pd  # noqa: E402
import v5_reclass as V  # noqa: E402

t = pd.DataFrame(V.cross_block())
for c in V.METRICS:
    if c in t:
        t[c] = t[c].map(lambda x: None if x is None or (isinstance(x, float) and math.isnan(x)) else math.trunc(x * 10000) / 10000)
t.to_csv(Path(__file__).resolve().parent / "interim_r5.csv", index=False)
with pd.option_context("display.width", 250, "display.max_rows", 300, "display.max_columns", 30):
    print(t[["generator", "classifier", "dataset", "mode", "touch", "fully_v4", "fully_r5", "no_action_v4", "no_action_r5", "no_action_r5_7"]])
