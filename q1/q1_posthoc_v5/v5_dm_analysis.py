"""POST HOC (S-P5), matched three-disease comparison: analysis (plan Section 6). Reads files only.

For the NHANES diabetes runs (v5_dm_runs.py) and, recomputed with the same function from their stored runs, CKD with
the socio-economic features frozen (S-P1, ses_freeze) and HTN main: test AUC, prevalence, eligible and cohort size,
single non-indicator flip share, O-A1 fully unactionable (action = lever or treatable of the domain), no-action
share (non-empty change set without a lever or treatable, over all returned counterfactuals; patient means), touch
share, O-A2 movability null (100,000 draws, seed 20261111), O-A3 valid among requested lock - published, lock
coverage, share of counterfactuals changing BMI (published, lock), XGBoost total-gain shares. The statistics are the
frozen A2 helpers (q1_domain_ckd/a2_domain.py: oshare, patient_null, movability_null_p, boot_means, clopper_pearson).
The CKD and HTN values are checked against their stored results (results_main.json); a mismatch stops the script.
H1 and H2 decision rules applied descriptively.

Usage (P4 or p7-carla312 venv, needs xgboost): python -I v5_dm_analysis.py
Output: outputs/q1_posthoc_v5/analysis/matched_three_disease.json
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(HERE.parent / "q1_domain_ckd"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import a2_domain as D  # noqa: E402

O = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs")
PLAN = Path("D:/20-study/uit/research/diabetesxai/paper7/prereg/posthoc_v5_plan_en_v1_20261112_1211.md")
PLAN_SHA256 = open(HERE / "PLAN_SHA256.txt", encoding="utf-8").read().split()[0]
SEEDS = [42, 123, 2024, 7, 31337]
REQ = 25
DM = O / "q1_posthoc_v5" / "nhanes_dm"
RUNS = {
    "diabetes_a1c": (DM / "runs_dm_a1c", "dm_told"),
    "diabetes_diag": (DM / "runs_dm_diag", "dm_told"),
    "diabetes_hbp_measured": (DM / "runs_dm_hbp_measured", "dm_measured"),
    "ckd_ses_freeze": (O / "q1_posthoc_ses_splits" / "ses_freeze" / "a2_runs_main", "ckd"),
    "htn_main": (O / "q1_domain_htn" / "a2_runs_main", "htn"),
}
STORED = {"ckd_ses_freeze": O / "q1_posthoc_ses_splits" / "ses_freeze" / "a2_analysis" / "results_main.json",
          "htn_main": O / "q1_domain_htn" / "a2_analysis" / "results_main.json"}
MODEL = {"ckd_ses_freeze": O / "q1_domain_ckd" / "a2_model" / "xgb_ckd.json",
         "htn_main": O / "q1_domain_htn" / "a2_model" / "xgb_htn.json"}
PREV = {"ckd_ses_freeze": (O / "q1_domain_ckd" / "a0_nhanes_ckd", "CKD_label"),
        "htn_main": (O / "q1_domain_htn" / "a0_nhanes_htn" / "nhanes_htn_analytic_2017-2023.csv", "HTN_L1_measured")}


def roles(kind):
    if kind == "ckd":
        t = pd.read_csv(O / "q1_domain_ckd" / "a0_role_table" / "ckd_role_table.csv")
    elif kind == "htn":
        t = pd.read_csv(O / "q1_domain_htn" / "a0_role_table" / "htn_role_table.csv")
    else:
        t = pd.read_csv(DM / "dm_role_table.csv")
    r = dict(zip(t.variable, t.role))
    if kind == "dm_measured":
        r["HighBP"] = "treatable"
    return r


def tr(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else math.trunc(x * 10000) / 10000


def q(bs, p):
    return float(np.quantile(bs, p))


def sets(series):
    return [set(s.split(";")) - {""} for s in series.fillna("")]


def gain(path):
    import xgboost as xgb
    b = xgb.Booster()
    b.load_model(str(path))
    g = b.get_score(importance_type="total_gain")
    tot = sum(g.values())
    return {f: v / tot for f, v in sorted(g.items(), key=lambda kv: -kv[1])}


def analyse(name, run, kind):
    role = roles(kind)
    inds = {f for f, r in role.items() if r == "indicator"}
    act = {f for f, r in role.items() if r in ("lever", "treatable")}
    info = json.loads((run / "run_info.json").read_text(encoding="utf-8"))
    coh = pd.read_csv(run / "cohort.csv")
    n = len(coh)
    pids = coh["pid"].to_numpy()
    mov = pd.read_csv(run / "movability.csv").fillna({"movable": ""})
    dice = {m: pd.concat([pd.read_csv(run / f"dice_{m}_seed{s}.csv") for s in SEEDS], ignore_index=True)
            for m in ("published", "lock")}
    res = {"run": str(run), "n_cohort": n, "test_auc": info["test_auc"], "eligible": info.get("eligible_p_ge_0.5"),
           "single_nonindicator_flip_share": info["pre_generator_single_nonindicator_flip_share"],
           "action_features": sorted(act), "indicators": sorted(inds)}
    per_mode = {}
    for m, d in dice.items():
        S = sets(d["changed"])
        d = d.assign(fully=[bool(s & inds) and not (s & act) for s in S], touch=[bool(s & inds) for s in S],
                     no_action=[bool(s) and not (s & act) for s in S], empty=[not s for s in S],
                     bmi=["BMI" in s for s in S], ses_only=[bool(s) and s <= {"Income", "Education", "AnyHealthcare"} for s in S],
                     n_ind=[len(s & inds) for s in S], n_chg=[len(s) for s in S])
        dice[m] = d
        pm = d.groupby("pid")[["fully", "touch", "no_action", "empty", "bmi", "valid"]].mean()
        per_mode[m] = {"n_cf": int(len(d)), "n_patients_with_cf": int(pm.shape[0]),
                       **{f"{c}_patient_mean": float(pm[c].mean()) for c in pm.columns},
                       "no_action_pooled": float(d["no_action"].mean())}
    res["dice"] = per_mode
    dp = dice["published"]
    per = dp.groupby("pid").agg(fully=("fully", "mean"), ind=("n_ind", "sum"), chg=("n_chg", "sum")).reindex(pids).dropna()
    bs = D.boot_means(per["fully"].to_numpy())
    res["O_A1"] = {"est": float(per["fully"].mean()), "lower_one_sided_99": q(bs, 0.01), "upper_one_sided_99": q(bs, 0.99),
                   "ci95": [q(bs, 0.025), q(bs, 0.975)]}
    na = dp.groupby("pid")["no_action"].mean().reindex(pids).dropna().to_numpy()
    bs = D.boot_means(na)
    res["no_action"] = {"est": float(na.mean()), "ci95": [q(bs, 0.025), q(bs, 0.975)]}
    movd = {int(r.pid): [f for f in r.movable.split(";") if f] for r in mov.itertuples()}
    observed, nulls = [], []
    for pid, g in dp.groupby("pid"):
        cnt = Counter(f for s in sets(g["changed"]) for f in s)
        M = movd[int(pid)]
        observed.append(D.oshare(cnt, [f for f in cnt if f in inds]))
        nulls.append(D.patient_null(cnt, M, sum(f in inds for f in M)))
    T, p, n_ge = D.movability_null_p(observed, nulls, draws=100_000, seed=20261111)
    res["O_A2"] = {"T": T, "null_mean": float(np.mean([v.mean() for v in nulls])), "p": p}
    vr = {m: dice[m].groupby("pid")["valid"].sum().reindex(pids).fillna(0).to_numpy() / REQ for m in dice}
    bs = D.boot_means(vr["lock"] - vr["published"])
    res["O_A3"] = {"est": float((vr["lock"] - vr["published"]).mean()), "lower_one_sided_99": q(bs, 0.01),
                   "upper_one_sided_99": q(bs, 0.99), "published": float(vr["published"].mean()), "lock": float(vr["lock"].mean())}
    cov = {m: int((dice[m][dice[m]["valid"] == 1].groupby("pid").size().reindex(pids).fillna(0) > 0).sum()) for m in dice}
    res["coverage"] = {m: {"x": cov[m], "n": n, "share": cov[m] / n} for m in cov}
    lo, hi = res["O_A1"]["lower_one_sided_99"], res["O_A1"]["upper_one_sided_99"]
    res["H1_rule_descriptive"] = ("supported" if (lo > 0.10 and p < 0.01) else
                                  "not supported" if (hi <= 0.10 or p >= 0.5) else "undecided")
    lc = cov["lock"] / n
    res["H2_rule_descriptive"] = ("supported" if (res["O_A3"]["lower_one_sided_99"] > -0.05 and lc >= 0.95) else
                                  "not supported" if (res["O_A3"]["upper_one_sided_99"] < -0.05 or lc < 0.95) else "undecided")
    mp = MODEL.get(name, run / "xgb_dm.json")
    g = gain(mp)
    res["gain_share"] = {"BMI": g.get("BMI", 0.0), "GenHlth": g.get("GenHlth", 0.0), "MentHlth": g.get("MentHlth", 0.0),
                         "top5": dict(list(g.items())[:5])}
    if "flow" in info:
        res["n_analytic"], res["prevalence"] = info["flow"]["complete_cases"], info["flow"]["prevalence"]
    return res


def prevalence_other(name):
    p, col = PREV[name]
    if p.is_dir():
        p = next(p.glob("*analytic*.csv"))
    d = pd.read_csv(p)
    return int(len(d)), float((d[col] == 1).mean())


def check_stored(name, r):
    s = json.loads(STORED[name].read_text(encoding="utf-8"))
    pairs = [(r["O_A1"]["est"], s["O_A1_fully_unactionable_dice_published"]["est"]),
             (r["O_A2"]["p"], s["O_A2_movability_null"]["p"]),
             (r["O_A3"]["est"], s["O_A3_valid_among_requested_lock_minus_published"]["est"]),
             (r["coverage"]["lock"]["share"], s["coverage_dice"]["lock"]["share"]),
             (r["test_auc"], s["test_auc"])]
    bad = [(a, b) for a, b in pairs if abs(a - b) > 1e-9]
    if bad:
        sys.exit(f"{name}: recomputed values differ from the stored results: {bad}")
    return "recomputed O-A1, O-A2 p, O-A3, lock coverage and AUC equal the stored results"


def main():
    import hashlib
    if hashlib.sha256(PLAN.read_bytes()).hexdigest() != PLAN_SHA256:
        sys.exit("S-P5 plan hash mismatch")
    out = {"label": "POST HOC (S-P5), exploratory; prevalence differences are descriptive",
           "written": datetime.now().strftime("%d/%m/%Y %H:%M"), "plan_sha256": PLAN_SHA256}
    for name, (run, kind) in RUNS.items():
        if not (run / "dice_lock_seed31337.csv").exists():
            out[name] = {"status": "not run"}
            continue
        r = analyse(name, run, kind)
        if name in STORED:
            r["stored_check"] = check_stored(name, r)
            r["n_analytic"], r["prevalence"] = prevalence_other(name)
        out[name] = r
        print(name, {k: (tr(v["est"]) if isinstance(v, dict) and "est" in v else None) for k, v in r.items()
                     if k in ("O_A1", "no_action", "O_A3")}, "p", tr(r["O_A2"]["p"]), "AUC", tr(r["test_auc"]), flush=True)
    d = O / "q1_posthoc_v5" / "analysis"
    d.mkdir(parents=True, exist_ok=True)
    (d / "matched_three_disease.json").write_text(json.dumps(out, indent=2, default=float) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
