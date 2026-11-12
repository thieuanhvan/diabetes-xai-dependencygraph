"""POST HOC (S-P5), exploratory: presentation-layer counts of route-aware outputs under role reading R5 (plan
Section 3, last item). Reads stored outputs only; added after the first S-P5 recount (engineering entry, own hash).

Per route-aware output set: share of outputs with at least one action (v4 reading: lever or treatable; R5: a
feature of L5), share that move an indicator, and share that move an indicator with no R5 action (an output the
three-part presentation rule would show without any action). Shares are pooled over outputs (valid / kept outputs,
as in the source tables).
Usage (p7-carla312 venv): python -I v5_presentation_r5.py
Output: outputs/q1_posthoc_v5/reclass/presentation_r5.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
from depgraph.nodes import TIER  # noqa: E402

PAPER7 = Path("D:/20-study/uit/research/diabetesxai/paper7")
PLAN = PAPER7 / "prereg" / "posthoc_v5_plan_en_v1_20261112_1211.md"
PLAN_SHA256 = open(HERE / "PLAN_SHA256.txt", encoding="utf-8").read().split()[0]
O = PAPER7 / "outputs"
IND = {f for f, r in TIER.items() if r == "indicator"}
V4 = {f for f, r in TIER.items() if r in ("lever", "treatable")}
L5 = {"BMI", "PhysActivity", "Fruits", "Veggies", "Smoker", "HvyAlcoholConsump"}
DS = {"brfss2021": "_xgbrand", "nhis2022": "_v2", "nhis2024": "_v2", "nhanes2017-2020_diag": "_v3",
      "nhanes2017-2020_a1c": "_v3", "nhanes2021-2023_diag": "_v3", "nhanes2021-2023_a1c": "_v3"}


def shares(changed):
    S = [set(str(s).split(";")) - {"", "nan"} for s in changed.fillna("")]
    n = len(S)
    if not n:
        return {"n": 0}
    return {"n": n, "with_action_v4": sum(bool(s & V4) for s in S) / n,
            "with_action_r5": sum(bool(s & L5) for s in S) / n,
            "touch_indicator": sum(bool(s & IND) for s in S) / n,
            "indicator_without_r5_action": sum(bool(s & IND) and not (s & L5) for s in S) / n,
            "nonempty_without_r5_action": sum(bool(s) and not (s & L5) for s in S) / n,
            "highbp_or_highchol_only_action_v4": sum(bool(s & V4) and not (s & L5) for s in S) / n}


def main():
    if hashlib.sha256(PLAN.read_bytes()).hexdigest() != PLAN_SHA256:
        sys.exit("S-P5 plan hash mismatch")
    res = {"label": "POST HOC (S-P5), exploratory; presentation-layer counts of route-aware outputs under R5",
           "written": datetime.now().strftime("%d/%m/%Y %H:%M"), "plan_sha256": PLAN_SHA256, "rows": {}}
    R = O / "crossdataset_p4" / "results"
    for ds, t in DS.items():
        f = R / f"cross_{ds}{t}_changes.csv"
        d = pd.read_csv(f)
        d = d[d["mode"].astype(str).str.startswith("route")]
        if len(d):
            res["rows"][f"dice_random_xgb_{ds}"] = shares(d["changed"])
    B = O / "q1_ext_b"
    for name, f in (("actionable_recourse_l1", B / "ar_lr" / "out_route.csv"),
                    ("actionable_recourse_native", O / "q1_posthoc_ses_splits" / "ar_lr_mps" / "out_route.csv"),
                    ("growing_spheres", B / "gs_xgb" / "out_route.csv")):
        d = pd.read_csv(f)
        d = d[d["valid_post"] == True]  # noqa: E712
        res["rows"][name] = shares(d["changed"])
    res["rows"]["wachter_lr"] = shares(pd.read_csv(B / "wachter_lr" / "kept_route.csv")["changed"])
    for s in (44, 45, 46, 48, 49):
        res["rows"][f"wachter_mlp_s{s}"] = shares(pd.read_csv(O / "q1_ext_b_posthoc" / f"wachter_mlp_s{s}" / "kept_route.csv")["changed"])
    d = O / "q1_posthoc_v5" / "reclass"
    d.mkdir(parents=True, exist_ok=True)
    (d / "presentation_r5.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    for k, v in res["rows"].items():
        print(k, {a: (round(b, 6) if isinstance(b, float) else b) for a, b in v.items()})


if __name__ == "__main__":
    main()
