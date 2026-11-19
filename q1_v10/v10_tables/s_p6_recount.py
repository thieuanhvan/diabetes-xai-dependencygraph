"""POST HOC (S-P6), exploratory: recount of stored outputs, no new run (plan posthoc_plan_s_p6_valid_only_readings_v1).
# v10 copy (18/11 22:3x): reproduction targets set to the v10 values (CKD no action 0.3159; route-aware 0.7150, FL-L 0.1400); v9 targets were 0.3029, 0.6883, 0.1433.

(A) no-action and fully-unactionable shares with the denominator restricted to valid outputs, next to the published
    all-returned value (reproduced from the same files and checked against the stored results; a mismatch stops).
(B) reading R6 (diabetes surveys): R5 without Smoker (ever smoked 100 cigarettes).
(C) reading NB: BMI not an action, every domain (descriptive); action coverage of route-aware and FL-L kept outputs
    under R5 and NB-R5 on networks 46, 48, 49.
Shares: per output, no action = non-empty change set without an action feature; fully unactionable = touches an
indicator and has no action feature. Patient means over patients with at least one output in the denominator.
Patient bootstrap 95% percentile intervals (2,000 resamples, default_rng(20261118)) for headline rows. Truncated.

Usage (repo .venv): python -I s_p6_recount.py
Output: outputs/q1_posthoc_s_p6/recount_s_p6.json and recount_s_p6.csv
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
sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
from depgraph.nodes import TIER  # noqa: E402

PAPER7 = Path("D:/20-study/uit/research/diabetesxai/paper7")
PLAN = PAPER7 / "prereg" / "posthoc_plan_s_p6_valid_only_readings_v1_20261118_0908.md"
PLAN_SHA256 = open(HERE / "PLAN_SHA256.txt", encoding="utf-8").read().split()[0]
O = PAPER7 / "outputs" / "p5_v10" / "outputs"
R = O / "crossdataset_p4" / "results"
OUT = O / "q1_posthoc_s_p6"
SEEDS = [42, 123, 2024, 7, 31337]
DS = ["brfss2021", "nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c",
      "nhanes2021-2023_diag", "nhanes2021-2023_a1c"]
XGB_RANDOM = {"brfss2021": "_xgbrand", "nhis2022": "_v2", "nhis2024": "_v2"}
IND_DM = {f for f, r in TIER.items() if r == "indicator"}
L5 = {"BMI", "PhysActivity", "Fruits", "Veggies", "Smoker", "HvyAlcoholConsump"}
DM_READINGS = {"v4": {f for f, r in TIER.items() if r in ("lever", "treatable")}, "r5": L5, "r6": L5 - {"Smoker"},
               "nb_r5": L5 - {"BMI"}, "nb_r6": L5 - {"BMI", "Smoker"}}
B, RNG_SEED = 2000, 20261118


def tr(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else math.trunc(x * 10000) / 10000


def sets(series):
    return [set(str(s).split(";")) - {"", "nan"} for s in series.fillna("")]


def per_patient(d, inds, readings):
    S = sets(d["changed"])
    cols = {"touch": [bool(s & inds) for s in S]}
    for k, A in readings.items():
        cols[f"no_action_{k}"] = [bool(s) and not (s & A) for s in S]
        cols[f"fully_{k}"] = [bool(s & inds) and not (s & A) for s in S]
    return d.assign(**cols).groupby("pid")[list(cols)].mean()


def boot(x):
    rng = np.random.default_rng(RNG_SEED)
    n = len(x)
    bs = np.array([x[rng.integers(0, n, n)].mean() for _ in range(B)])
    return [tr(float(np.quantile(bs, 0.025))), tr(float(np.quantile(bs, 0.975)))]


def block(meta, d, inds, readings, headline_keys=()):
    rows = []
    for denom, dd in (("all", d), ("valid", d[d["valid"] == 1])):
        pm = per_patient(dd, inds, readings) if len(dd) else None
        r = {**meta, "denominator": denom, "n_patients": 0 if pm is None else int(len(pm)), "n_outputs": int(len(dd))}
        if pm is not None:
            for c in pm.columns:
                r[c] = tr(float(pm[c].mean()))
            for k in headline_keys:
                r[f"ci95_{k}"] = boot(pm[k].to_numpy())
        rows.append(r)
    return rows


def read_cross(ds, t):
    fc, fs = R / f"cross_{ds}{t}_changes.csv", R / f"cross_{ds}{t}_summary.csv"
    if not fc.exists():
        return None
    ch = pd.read_csv(fc)
    for suf in "bc":
        extra = R / f"cross_{ds}{t}{suf}_summary.csv"
        if extra.exists():
            s2 = pd.read_csv(extra)
            c2 = pd.read_csv(R / f"cross_{ds}{t}{suf}_changes.csv")
            ch = pd.concat([ch[~ch.seed.isin(s2.seed)], c2], ignore_index=True)
    return ch


def diabetes_surveys(stop):
    ref = pd.read_csv(O / "q1_posthoc_v5" / "reclass" / "reclass_r5_table.csv")
    rows = []
    for gen, clfs in (("dice_random", ["xgb", "lr", "rf"]), ("dice_genetic", ["xgb"]), ("exhaustive", ["xgb", "lr", "rf"])):
        for clf in clfs:
            for ds in DS:
                if gen == "dice_random":
                    t = XGB_RANDOM.get(ds, "_v3") if clf == "xgb" else f"_{clf}"
                elif gen == "dice_genetic":
                    t = "_gen2"
                else:
                    t = "_exh" if clf == "xgb" else f"_{clf}_exh"
                ch = read_cross(ds, t)
                if ch is None:
                    continue
                for mode in ("published", "tableV"):
                    d = ch[ch["mode"] == mode]
                    if not len(d):
                        continue
                    m = "lock" if mode == "tableV" else mode
                    head = ("no_action_v4", "no_action_r5") if (gen == "dice_random" and clf == "xgb" and m == "published") else ()
                    rr = block({"domain": "diabetes_survey", "generator": gen, "classifier": clf, "dataset": ds, "mode": m},
                               d, IND_DM, DM_READINGS, head)
                    a = rr[0]
                    x = ref[(ref.generator == gen) & (ref.classifier == clf) & (ref.dataset == ds) & (ref["mode"] == m)]
                    if len(x):
                        for k in ("no_action_v4", "no_action_r5", "fully_v4", "fully_r5", "touch"):
                            if abs(a[k] - float(x[k].iloc[0])) > 1e-4:
                                stop.append(f"{gen}/{clf}/{ds}/{m} {k}: {a[k]} vs stored {float(x[k].iloc[0])}")
                        for r in rr:
                            r["reproduced"] = True
                    rows += rr
    return rows


def roles(path, hbp_treatable=False):
    t = pd.read_csv(path)
    r = dict(zip(t.variable, t.role))
    if hbp_treatable:
        r["HighBP"] = "treatable"
    return r


def nhanes_domains(stop):
    CKD_RT = O / "q1_domain_ckd" / "a0_role_table" / "ckd_role_table.csv"
    HTN_RT = O / "q1_domain_htn" / "a0_role_table" / "htn_role_table.csv"
    DM_RT = O / "q1_posthoc_v5" / "nhanes_dm" / "dm_role_table.csv"
    SS = O / "q1_posthoc_ses_splits"
    sets_ = [("ckd_main", O / "q1_domain_ckd" / "a2_runs_main", CKD_RT, False),
             ("ckd_less_exposed", O / "q1_domain_ckd" / "a2_runs_less_exposed", CKD_RT, False),
             ("ckd_ses_freeze", SS / "ses_freeze" / "a2_runs_main", CKD_RT, False)]
    sets_ += [(f"ckd_split_{s}", SS / f"split_{s}" / "a2_runs_main", CKD_RT, False) for s in (11, 22, 33, 44, 55)]
    sets_ += [("htn_main", O / "q1_domain_htn" / "a2_runs_main", HTN_RT, False),
              ("matched_dm_a1c", O / "q1_posthoc_v5" / "nhanes_dm" / "runs_dm_a1c", DM_RT, False),
              ("matched_dm_diag", O / "q1_posthoc_v5" / "nhanes_dm" / "runs_dm_diag", DM_RT, False),
              ("matched_dm_hbp_measured", O / "q1_posthoc_v5" / "nhanes_dm" / "runs_dm_hbp_measured", DM_RT, True)]
    headline = {"ckd_main", "ckd_ses_freeze", "htn_main", "matched_dm_a1c", "matched_dm_diag"}
    matched = json.loads((O / "q1_posthoc_v5" / "analysis" / "matched_three_disease.json").read_text(encoding="utf-8"))
    mkey = {"ckd_ses_freeze": "ckd_ses_freeze", "htn_main": "htn_main", "matched_dm_a1c": "diabetes_a1c",
            "matched_dm_diag": "diabetes_diag", "matched_dm_hbp_measured": "diabetes_hbp_measured"}
    rows = []
    for name, run, rt, hbp in sets_:
        if not (run / "dice_lock_seed31337.csv").exists():
            rows.append({"domain": name, "status": "not stored"})
            continue
        role = roles(rt, hbp)
        inds = {f for f, r in role.items() if r == "indicator"}
        act = {f for f, r in role.items() if r in ("lever", "treatable")}
        rd = {"graph": act, "nb": act - {"BMI"}}
        for mode in ("published", "lock"):
            d = pd.concat([pd.read_csv(run / f"dice_{mode}_seed{s}.csv") for s in SEEDS], ignore_index=True)
            head = ("no_action_graph", "no_action_nb") if (name in headline and mode == "published") else ()
            rr = block({"domain": name, "generator": "dice_random", "classifier": "xgb", "dataset": "nhanes_2017-2023",
                        "mode": mode, "action_features": ";".join(sorted(act))}, d, inds, rd, head)
            if mode == "published":
                a = rr[0]
                if name in mkey:
                    ref = matched[mkey[name]]["no_action"]["est"]
                    if abs(a["no_action_graph"] - tr(ref)) > 1e-4:
                        stop.append(f"{name} no_action: {a['no_action_graph']} vs stored {ref}")
                    rr[0]["reproduced"] = True
                if name == "ckd_main" and abs(a["no_action_graph"] - 0.3159) > 1e-4:
                    stop.append(f"ckd_main no_action: {a['no_action_graph']} vs v10 manuscript 0.3159")
                elif name == "ckd_main":
                    rr[0]["reproduced"] = True
            rows += rr
    return rows


def forced_lever():
    act_r5, act_nb = L5, L5 - {"BMI"}
    out = {}
    for mode, f in (("route_aware", lambda s: O / "q1_ext_b_posthoc" / f"wachter_mlp_s{s}" / "kept_route.csv"),
                    ("fl_l", lambda s: O / "q1_posthoc_v5" / f"wachter_mlp_s{s}" / "kept_levers.csv")):
        cov = a5 = anb = 0
        for s in (46, 48, 49):
            d = pd.read_csv(f(s))
            S = sets(d["changed"])
            d = d.assign(r5=[bool(x & act_r5) for x in S], nb=[bool(x & act_nb) for x in S])
            g = d.groupby("pid")[["r5", "nb"]].any()
            cov += len(g)
            a5 += int(g["r5"].sum())
            anb += int(g["nb"].sum())
        out[mode] = {"units": 600, "coverage": tr(cov / 600), "action_coverage_r5": tr(a5 / 600),
                     "action_coverage_nb_r5": tr(anb / 600)}
    out["check"] = "published pooled coverage: route-aware 0.7150, FL-L 0.1400 (v10)"
    return out


def main():
    if hashlib.sha256(PLAN.read_bytes()).hexdigest() != PLAN_SHA256:
        sys.exit("S-P6 plan hash mismatch")
    stop = []
    rows = diabetes_surveys(stop) + nhanes_domains(stop)
    fl = forced_lever()
    if abs(fl["route_aware"]["coverage"] - 0.7150) > 1e-4 or abs(fl["fl_l"]["coverage"] - 0.1400) > 1e-4:
        stop.append(f"forced-lever coverage not reproduced: {fl}")
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"label": "POST HOC (S-P6), exploratory, recount of stored outputs, no new run",
           "written": datetime.now().strftime("%d/%m/%Y %H:%M"), "plan_sha256": PLAN_SHA256,
           "readings_diabetes_surveys": {k: sorted(v) for k, v in DM_READINGS.items()},
           "reproduction_mismatches": stop, "rows": rows, "forced_lever_networks_46_48_49": fl,
           "not_recounted": "extension-B generators (AR both costs, Growing Spheres, Wachter LR and networks, MINT) "
                            "already use valid/kept outputs"}
    (OUT / "recount_s_p6.json").write_text(json.dumps(res, indent=2, default=float) + "\n", encoding="utf-8")
    pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("ci95")} for r in rows]).to_csv(OUT / "recount_s_p6.csv", index=False)
    if stop:
        print("REPRODUCTION MISMATCH:\n" + "\n".join(stop))
        sys.exit(1)
    print("all reproduced; rows", len(rows), "FL", fl)


if __name__ == "__main__":
    main()
