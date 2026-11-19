"""Main-text numbers of manuscript v9, recomputed from the v9 outputs and from the v10 re-run (P5 0.2.1 frames).

Reuses the functions of the 0.2.0 measurement run (p5_migration/collect_headline.py, imported read only) with the
v10 output tree; adds Table 4 for all seven configurations (BRFSS _xgbrand, NHIS _v2, NHANES _v3) and the reading
R5 band. The v9 recomputation is checked against the printed v9 numbers before anything is written (as before).
Usage (p7-carla312 venv): python -I collect_v10.py  -> collect_v10.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(HERE.parent / "p5_migration"))
import collect_headline as CH  # noqa: E402

O9 = CH.O
O10 = HERE / "outputs"
TAG = {"brfss2021": "_xgbrand", "nhis2022": "_v2", "nhis2024": "_v2"}
DS = ["brfss2021", "nhis2022", "nhis2024"] + CH.T4


def paths(v):
    b = O9 if v == "v9" else O10
    fr = ({"ckd": b / "q1_domain_ckd" / "a0_nhanes_ckd" / "nhanes_ckd_analytic_2017-2023.csv",
           "htn": b / "q1_domain_htn" / "a0_nhanes_htn" / "nhanes_htn_analytic_2017-2023.csv"})
    return {"ckd": b / "q1_domain_ckd", "ses": b / "q1_posthoc_ses_splits" / "ses_freeze", "htn": b / "q1_domain_htn",
            "dm": b / "q1_posthoc_v5" / "nhanes_dm", "t4": b / "crossdataset_p4" / "results",
            "ckd_model": b / "q1_domain_ckd" / "a2_model" / "xgb_ckd.json", "frames": fr}


def t4_row(rdir, ds):
    tag = TAG.get(ds, "_v3")
    f, s = rdir / f"cross_{ds}{tag}_changes.csv", rdir / f"cross_{ds}{tag}_summary.csv"
    if not f.exists() or len(pd.read_csv(s)) < 15:
        return None
    tmp = rdir / "__t4tmp"
    tmp.mkdir(exist_ok=True)
    # CH.t4_row reads cross_<ds>_v3_*: give it the right files under that name in a temporary folder
    for a, b in ((f, tmp / f"cross_{ds}_v3_changes.csv"), (s, tmp / f"cross_{ds}_v3_summary.csv")):
        if b.exists():
            b.unlink()
        b.write_bytes(a.read_bytes())
    r = CH.t4_row(tmp, ds)
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    return r


def main():
    CH.P = paths
    res = {}
    for v in ("v9", "v10"):
        r = CH.nhanes(v)
        r["t4"] = {ds: t4_row(paths(v)["t4"], ds) for ds in DS}
        res[v] = r
    bad = CH.check_v9(res["v9"])
    if bad:
        sys.exit(f"v9 recomputation differs from the manuscript: {bad}")
    for v in res:
        rows = [x for x in res[v]["t4"].values() if x]
        res[v]["r5_band"] = [min(x["no_action_r5"] for x in rows), max(x["no_action_r5"] for x in rows)]
        res[v]["prespec_band"] = [min(x["no_action_v4"] for x in rows), max(x["no_action_v4"] for x in rows)]
        for k in ("touch", "unsup", "fully"):
            res[v][f"{k}_band"] = [min(x[k] for x in rows), max(x[k] for x in rows)]
    (HERE / "collect_v10.json").write_text(json.dumps(res, indent=2, default=float) + "\n", encoding="utf-8")
    F = {v: CH.flat(res[v]) for v in res}
    t = pd.DataFrame([{"quantity": k, "v9": F["v9"].get(k), "v10": F["v10"].get(k)} for k in F["v9"]])
    t.to_csv(HERE / "collect_v10.csv", index=False, lineterminator="\n")
    print(t.to_string(index=False))


if __name__ == "__main__":
    main()
