"""POST HOC (S-P5), exploratory: diabetes metrics under role reading R5 (plan Sections 2-3). Reads files only.

R5 (BRFSS, NHIS, harmonised NHANES diabetes tables): action features = the genuine behaviours BMI, PhysActivity,
Fruits, Veggies, Smoker, HvyAlcoholConsump; HighBP and HighChol (ever told) are diagnosis history and NoDocbcCost an
access barrier, all non-actionable. R5-7: R5 plus NoDocbcCost as an action. v4: lever or treatable (as published).
Per output: no action = non-empty change set without an action feature; fully unactionable = touches an indicator
and has no action feature; touch = touches an indicator. Unsupported at k = 1 (lever sources) is recomputed to
confirm it does not change. Shares are patient means, as in the source tables:
  DiCE random / genetic (crossdataset_p4 results): mean over all returned counterfactuals of a patient, averaged
     over cohort patients (p7_classifier_tables convention; modes published and tableV = indicator lock);
  exhaustive search: mean over the returned change sets of a patient (published, lock);
  extension B (AR both costs, GS, Wachter/LR, MINT) and the B-P1 networks: valid / kept outputs only, patient means
     (b_analysis convention).
Usage (p7-carla312 venv): python -I v5_reclass.py
Output: outputs/q1_posthoc_v5/reclass/reclass_r5.json and reclass_r5_table.csv
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "crossdataset_p4"))
sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
from depgraph.audit import classify  # noqa: E402
from depgraph.nodes import TIER  # noqa: E402

PAPER7 = Path("D:/20-study/uit/research/diabetesxai/paper7")
PLAN = PAPER7 / "prereg" / "posthoc_v5_plan_en_v1_20261112_1211.md"
PLAN_SHA256 = open(HERE / "PLAN_SHA256.txt", encoding="utf-8").read().split()[0]
O = PAPER7 / "outputs"
R = O / "crossdataset_p4" / "results"
DS = ["brfss2021", "nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c",
      "nhanes2021-2023_diag", "nhanes2021-2023_a1c"]
XGB_RANDOM = {"brfss2021": "_xgbrand", "nhis2022": "_v2", "nhis2024": "_v2"}
IND = {f for f, r in TIER.items() if r == "indicator"}
L5 = {"BMI", "PhysActivity", "Fruits", "Veggies", "Smoker", "HvyAlcoholConsump"}
READINGS = {"v4": {f for f, r in TIER.items() if r in ("lever", "treatable")}, "r5": L5, "r5_7": L5 | {"NoDocbcCost"}}


def sets(series):
    return [set(str(s).split(";")) - {"", "nan"} for s in series.fillna("")]


def flags(S):
    out = {"touch": [bool(s & IND) for s in S],
           "unsup_k1": [classify(s, reading="narrow", rule="edge")["unsupported"] for s in S]}
    for k, A in READINGS.items():
        out[f"no_action_{k}"] = [bool(s) and not (s & A) for s in S]
        out[f"fully_{k}"] = [bool(s & IND) and not (s & A) for s in S]
    return out


METRICS = ["touch", "unsup_k1"] + [f"{m}_{k}" for k in READINGS for m in ("no_action", "fully")]


def patient_means(df, pid_col="pid", pats=None):
    d = df.assign(**flags(sets(df["changed"])))
    pm = d.groupby(pid_col)[METRICS].mean()
    if pats is not None:
        pm = pm.reindex(pats)
    return {m: float(np.nanmean(pm[m].to_numpy())) for m in METRICS} | {"n_patients": int(pm.notna().any(axis=1).sum()),
                                                                          "n_outputs": int(len(d))}


def read_cross(ds, t):
    fc, fs = R / f"cross_{ds}{t}_changes.csv", R / f"cross_{ds}{t}_summary.csv"
    if not fc.exists():
        return None, None
    s, ch = pd.read_csv(fs), pd.read_csv(fc)
    for suf in "bc":
        extra = R / f"cross_{ds}{t}{suf}_summary.csv"
        if extra.exists():
            s2 = pd.read_csv(extra)
            s = pd.concat([s[~s.seed.isin(s2.seed)], s2], ignore_index=True)
            c2 = pd.read_csv(R / f"cross_{ds}{t}{suf}_changes.csv")
            ch = pd.concat([ch[~ch.seed.isin(c2.seed)], c2], ignore_index=True)
    return s, ch


def cross_block():
    out = []
    for gen, clfs in (("dice_random", ["xgb", "lr", "rf"]), ("dice_genetic", ["xgb"]), ("exhaustive", ["xgb", "lr", "rf"])):
        for clf in clfs:
            for ds in DS:
                if gen == "dice_random":
                    t = XGB_RANDOM.get(ds, "_v3") if clf == "xgb" else f"_{clf}"
                elif gen == "dice_genetic":
                    t = "_gen2"
                else:
                    t = "_exh" if clf == "xgb" else f"_{clf}_exh"
                s, ch = read_cross(ds, t)
                if ch is None:
                    continue
                cohort = int(s.cohort.iloc[0])
                for mode in ("published", "tableV"):
                    d = ch[ch["mode"] == mode]
                    if not len(d):
                        continue
                    out.append({"generator": gen, "classifier": clf, "dataset": ds, "tag": t,
                                "mode": "lock" if mode == "tableV" else mode, "cohort": cohort,
                                **patient_means(d, pats=np.arange(cohort))})
    return out


def extb_block():
    out = []
    B = O / "q1_ext_b"
    items = [("actionable_recourse_l1", "lr", B / "ar_lr"), ("actionable_recourse_native", "lr", O / "q1_posthoc_ses_splits" / "ar_lr_mps"),
             ("growing_spheres", "xgb", B / "gs_xgb")]
    for gen, clf, base in items:
        for mode in ("published", "lock"):
            d = pd.read_csv(base / f"out_{mode}.csv")
            d = d[d["valid_post"] == True]  # noqa: E712
            out.append({"generator": gen, "classifier": clf, "dataset": "brfss2021", "mode": mode, "cohort": 200,
                        **patient_means(d, pats=np.arange(200))})
    for mode in ("published", "lock"):
        d = pd.read_csv(B / "wachter_lr" / f"kept_{mode}.csv")
        out.append({"generator": "wachter", "classifier": "lr", "dataset": "brfss2021", "mode": mode, "cohort": 200,
                    **patient_means(d, pats=np.arange(200))})
    d = pd.read_csv(B / "mint_xgb" / "out_published.csv")
    d = d[d["found"] == True]  # noqa: E712
    out.append({"generator": "mint", "classifier": "xgb", "dataset": "brfss2021", "mode": "published", "cohort": 200,
                **patient_means(d, pats=np.arange(200))})
    for s in (44, 45, 46, 48, 49):
        for mode in ("published", "lock", "route"):
            d = pd.read_csv(O / "q1_ext_b_posthoc" / f"wachter_mlp_s{s}" / f"kept_{mode}.csv")
            out.append({"generator": "wachter", "classifier": f"mlp_s{s}", "dataset": "brfss2021", "mode": mode,
                        "cohort": 200, **(patient_means(d, pats=np.arange(200)) if len(d) else {"n_outputs": 0})})
    return out


def tr(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else math.trunc(x * 10000) / 10000


def main():
    if hashlib.sha256(PLAN.read_bytes()).hexdigest() != PLAN_SHA256:
        sys.exit("S-P5 plan hash mismatch")
    rows = cross_block() + extb_block()
    res = {"label": "POST HOC (S-P5), exploratory; recomputed from stored outputs, no new run",
           "written": datetime.now().strftime("%d/%m/%Y %H:%M"), "plan_sha256": PLAN_SHA256,
           "readings": {k: sorted(v) for k, v in READINGS.items()}, "indicators": sorted(IND), "rows": rows}
    d = O / "q1_posthoc_v5" / "reclass"
    d.mkdir(parents=True, exist_ok=True)
    (d / "reclass_r5.json").write_text(json.dumps(res, indent=2, default=float) + "\n", encoding="utf-8")
    t = pd.DataFrame(rows)
    for c in METRICS:
        t[c] = t[c].map(tr)
    t.to_csv(d / "reclass_r5_table.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_rows", 200, "display.max_columns", 30):
        print(t[["generator", "classifier", "dataset", "mode", "touch", "fully_v4", "fully_r5", "no_action_v4", "no_action_r5",
                 "no_action_r5_7"]])


if __name__ == "__main__":
    main()
