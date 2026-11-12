"""POST HOC (S-P4), exploratory: results of the forced-lever baseline (plan Sections 6-9). Reads files only.

Wachter (BRFSS 2021): modes published, lock, route-aware (frozen B-P1 / extension B files) and forced (FL-G),
lockroute (FL-R) (S-P4 files), per model: MLP seeds 44, 45, 46, 48, 49 and LR.
CKD (NHANES, XGBoost main cohort): DiCE random and exhaustive search, published / lock / route-aware (A2 or S-P1
files) and forced (S-P4 files), configurations ses_freeze (primary in v4) and frozen (A2).
Readings of plan Section 7: Delta = coverage(route-aware) - coverage(forced), pooled over MLP seeds 46, 48, 49,
95% cluster bootstrap over test patients (2,000, default_rng(20261111)), margin 0.10.
Also: the reviewer's figures (Section 8) and the presentation-layer companion (Section 9).

Usage (p7-carla312 venv): python -I fl_analysis.py
Output: outputs/q1_posthoc_forced_lever/analysis/forced_lever_results.json
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
from scipy.stats import beta

HERE = Path(__file__).resolve().parent
sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
sys.path.insert(0, str(HERE.parent / "q1_domain_ckd"))

PAPER7 = Path("D:/20-study/uit/research/diabetesxai/paper7")
PLAN = PAPER7 / "prereg" / "posthoc_forced_lever_plan_en_v1_20261112_0957.md"
PLAN_SHA256 = "b1c7624aea42fa4e7911e869db77e71f44ccbe9dc983416acaf53c214cdf87e0"
O = PAPER7 / "outputs"
FL = O / "q1_posthoc_forced_lever"
MARGIN = 0.10
B, BSEED = 2000, 20261111
MLP_SEEDS = [44, 45, 46, 48, 49]
KEY_SEEDS = [46, 48, 49]
SES = {"Income", "Education", "AnyHealthcare"}
WMODES = ["published", "lock", "route", "forced", "lockroute"]


def cp(x, n, level=0.95):
    a = 1 - level
    lo = 0.0 if x == 0 else float(beta.ppf(a / 2, x, n - x + 1))
    hi = 1.0 if x == n else float(beta.ppf(1 - a / 2, x + 1, n - x))
    return [lo, hi]


def tr(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return math.trunc(x * 10000) / 10000


def output_shares(changed, roles):
    """Shares over outputs: touch indicator, GenHlth, no lever/treatable change, socio-economic only, and the
    presentation layer (actions = lever/treatable; consequences = indicators)."""
    sets = [set(s.split(";")) - {""} for s in changed.fillna("")]
    n = len(sets)
    if n == 0:
        return {"n": 0}
    act = [{f for f in s if roles.get(f) in ("lever", "treatable")} for s in sets]
    ind = [{f for f in s if roles.get(f) == "indicator"} for s in sets]
    ses = [s & SES for s in sets]
    return {"n": n,
            "touch_indicator": sum(bool(i) for i in ind) / n,
            "genhlth": sum("GenHlth" in s for s in sets) / n,
            "no_action": sum(not a for a in act) / n,
            "ses_only": sum(bool(s) and s <= SES for s in sets) / n,
            "ses_touch": sum(bool(x) for x in ses) / n,
            "presentation": {"with_consequence_shown": sum(bool(i) for i in ind) / n,
                             "with_at_least_one_action": sum(bool(a) for a in act) / n,
                             "action_list_empty_or_ses_only": sum(not a for a in act) / n,
                             "indicator_without_action": sum(bool(i) and not a for i, a in zip(ind, act)) / n}}


def cluster_boot_diff(df, a_col, b_col, B=B, seed=BSEED):
    """Mean of (a - b) over units with a cluster bootstrap over 'cluster' (ratio of sums)."""
    g = df.assign(v=df[a_col].astype(float) - df[b_col].astype(float)).groupby("cluster")["v"].agg(["sum", "count"])
    S, N = g["sum"].to_numpy(), g["count"].to_numpy()
    rng = np.random.default_rng(seed)
    bs = np.empty(B)
    for k in range(B):
        i = rng.integers(0, len(S), len(S))
        bs[k] = S[i].sum() / N[i].sum()
    return {"point": float(S.sum() / N.sum()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "n_units": int(N.sum()), "n_clusters": int(len(S))}


def reading(ci, m=MARGIN):
    if ci[1] <= m:
        return "lever forcing explains the coverage advantage (upper 95% bound <= margin)"
    if ci[0] > m:
        return "graph adds coverage beyond lever forcing (lower 95% bound > margin)"
    return "undecided"


def wachter_dirs(tag):
    if tag == "lr":
        return O / "q1_ext_b" / "wachter_lr", FL / "wachter_lr", O / "q1_ext_b" / "models" / "lr" / "cohort.csv"
    s = int(tag[1:])
    return (O / "q1_ext_b_posthoc" / f"wachter_mlp_s{s}", FL / f"wachter_mlp_s{s}",
            O / "q1_ext_b_posthoc" / "models" / f"mlp_s{s}" / "cohort.csv")


def wachter_block(tag, roles):
    old, new, cfile = wachter_dirs(tag)
    coh = pd.read_csv(cfile)
    n = len(coh)
    blk, cov = {"cohort_n": n}, {}
    for mode in WMODES:
        base = old if mode in ("published", "lock", "route") else new
        fr, fk = base / f"rows_{mode}.csv", base / f"kept_{mode}.csv"
        if not fr.exists():
            blk[mode] = {"status": "not run"}
            continue
        info = json.loads((base / "run_info.json").read_text(encoding="utf-8"))
        if info.get(f"status_{mode}") != "complete":
            blk[mode] = {"status": info.get(f"status_{mode}", "incomplete")}
            continue
        rows = pd.read_csv(fr).fillna({"changed": ""})
        try:
            kept = pd.read_csv(fk).fillna({"changed": ""})
        except pd.errors.EmptyDataError:
            kept = pd.DataFrame(columns=["pid", "changed", "cost", "valid_pre"])
        f = rows[rows["feasible"]]
        x = int(kept["pid"].nunique())
        last = int(rows["lsteps"].max()) if len(rows) else 0
        cov[mode] = pd.Series(0, index=range(n)).add(kept.groupby("pid").size(), fill_value=0) > 0
        blk[mode] = {
            "status": "complete",
            "coverage_x": x, "coverage": x / n, "coverage_cp95": cp(x, n),
            "kept_outputs": int(len(kept)), "valid_among_requested": len(kept) / (5 * n),
            "runs": int(len(rows)), "feasible_runs": int(len(f)),
            "valid_before_rounding": float(f["valid_pre"].mean()) if len(f) else None,
            "valid_after_rounding": float(f["valid_post"].mean()) if len(f) else None,
            "lost_at_rounding": float((f["valid_pre"] & ~f["valid_post"]).mean()) if len(f) else None,
            "valid_after_given_before": float(f.loc[f["valid_pre"], "valid_post"].mean()) if f["valid_pre"].any() else None,
            "patients_with_run_valid_before_rounding": int(f.loc[f["valid_pre"], "pid"].nunique()),
            "mean_iterations": float(f["iters"].mean()) if len(f) else None,
            "share_runs_at_last_lambda_step": float((f["lsteps"] == last).mean()) if len(f) else None,
            "last_lambda_step_index": last,
            "kept_mean_cost": float(kept["cost"].mean()) if len(kept) else None,
            "kept": output_shares(kept["changed"], roles),
            "cpu_hours": float(info.get(f"cpu_secs_{mode}", float("nan"))) / 3600}
        if mode == "forced" and "j1_equals_lock_share" in info:
            blk[mode]["j1_equals_lock_share"] = info["j1_equals_lock_share"]
    return blk, cov, coh


def ckd_block(cfg, roles_ckd):
    if cfg == "ses_freeze":
        old = O / "q1_posthoc_ses_splits" / "ses_freeze" / "a2_runs_main"
    else:
        old = O / "q1_domain_ckd" / "a2_runs_main"
    new = FL / f"ckd_{cfg}"
    coh = pd.read_csv(old / "cohort.csv")
    n = len(coh)
    seeds = [42, 123, 2024, 7, 31337]
    blk, cov = {"cohort_n": n}, {}
    for mode in ("published", "lock", "route", "forced"):
        base = new if mode == "forced" else old
        files = [base / f"dice_{mode}_seed{s}.csv" for s in seeds]
        if not all(p.exists() for p in files):
            blk[f"dice_{mode}"] = {"status": "not run"}
            continue
        d = pd.concat([pd.read_csv(p) for p in files], ignore_index=True).fillna({"changed": ""})
        v = d[d["valid"] == 1]
        x = int(v["pid"].nunique())
        cov[mode] = pd.Series(False, index=range(n))
        cov[mode].loc[v["pid"].unique()] = True
        blk[f"dice_{mode}"] = {"coverage_x": x, "coverage": x / n, "coverage_cp95": cp(x, n),
                               "returned": int(len(d)), "valid": int(len(v)),
                               "valid_among_requested": len(v) / (25 * n),
                               "all_returned": output_shares(d["changed"], roles_ckd),
                               "valid_only": output_shares(v["changed"], roles_ckd)}
    exh_old = pd.read_csv(old / "exhaustive.csv").fillna({"changed": ""})
    exh_new = new / "exhaustive_forced.csv"
    ex = {m: exh_old[exh_old["mode"] == m] for m in ("published", "lock", "route")}
    if exh_new.exists():
        ex["forced"] = pd.read_csv(exh_new).fillna({"changed": ""})
    best = {}
    for m, d in ex.items():
        b = d[d["round"] == 0].set_index("pid")["dist"]
        best[m] = b
        blk[f"exh_{m}"] = {"coverage_x": int(b.size), "coverage": b.size / n, "mean_best_cost": float(b.mean()) if b.size else None,
                           "all": output_shares(d["changed"], roles_ckd),
                           "best": output_shares(d[d["round"] == 0]["changed"], roles_ckd)}
    if "forced" in best:
        pair = sorted(set(best["forced"].index) & set(best["route"].index))
        diff = best["forced"].loc[pair].to_numpy() - best["route"].loc[pair].to_numpy()
        blk["exh_forced_minus_route_best_cost"] = {"n_pairs": len(pair), "mean": float(diff.mean()) if len(pair) else None,
                                                  "share_zero": float(np.mean(np.abs(diff) < 1e-12)) if len(pair) else None,
                                                  "share_negative": float(np.mean(diff < -1e-12)) if len(pair) else None}
    if "route" in cov and "forced" in cov:
        df = pd.DataFrame({"cluster": range(n), "r": cov["route"].to_numpy(), "f": cov["forced"].to_numpy()})
        res = cluster_boot_diff(df, "r", "f")
        blk["delta_dice_coverage_route_minus_forced"] = res | {"reading_descriptive": reading(res["ci95"])}
    return blk


def presentation_layer(roles, roles_ckd):
    out = {}
    for name, p in [("AR/LR range-scaled L1, route-aware", O / "q1_ext_b" / "ar_lr" / "out_route.csv"),
                    ("AR/LR native max percentile shift (S-P3), route-aware", O / "q1_posthoc_ses_splits" / "ar_lr_mps" / "out_route.csv"),
                    ("Wachter/LR, route-aware kept", O / "q1_ext_b" / "wachter_lr" / "kept_route.csv")]:
        d = pd.read_csv(p).fillna({"changed": ""})
        if "valid_post" in d.columns:
            d = d[d["valid_post"]]
        out[name] = output_shares(d["changed"], roles)
    for s in MLP_SEEDS:
        d = pd.read_csv(O / "q1_ext_b_posthoc" / f"wachter_mlp_s{s}" / "kept_route.csv").fillna({"changed": ""})
        out[f"Wachter/MLP seed {s}, route-aware kept"] = output_shares(d["changed"], roles)
    for cfg, base in [("ses_freeze", O / "q1_posthoc_ses_splits" / "ses_freeze" / "a2_runs_main"),
                      ("frozen", O / "q1_domain_ckd" / "a2_runs_main")]:
        d = pd.concat([pd.read_csv(base / f"dice_route_seed{s}.csv") for s in (42, 123, 2024, 7, 31337)]).fillna({"changed": ""})
        out[f"CKD DiCE route-aware, {cfg}, all returned"] = output_shares(d["changed"], roles_ckd)
        e = pd.read_csv(base / "exhaustive.csv").fillna({"changed": ""})
        out[f"CKD exhaustive route-aware best, {cfg}"] = output_shares(e[(e["mode"] == "route") & (e["round"] == 0)]["changed"], roles_ckd)
    return out


def reviewer_checks(W):
    s46 = W["s46"]
    chk = {
        "route_vs_published_coverage_s46": [s46["route"]["coverage_x"], s46["published"]["coverage_x"]],
        "route_vs_published_coverage_s49": [W["s49"]["route"]["coverage_x"], W["s49"]["published"]["coverage_x"]],
        "valid_before_rounding_route_vs_published_s46": [s46["route"]["valid_before_rounding"], s46["published"]["valid_before_rounding"]],
        "lock_s46_runs_valid_before_rounding": s46["lock"]["valid_before_rounding"],
        "lock_s46_runs_valid_after_rounding": s46["lock"]["valid_after_rounding"],
        "lock_s46_patients_with_run_valid_before_rounding": s46["lock"]["patients_with_run_valid_before_rounding"],
        "wachter_lr_published_lock_route_coverage": [W["lr"][m]["coverage_x"] for m in ("published", "lock", "route")],
    }
    gen = {}
    for s in KEY_SEEDS:
        b = W[f"s{s}"]
        gen[f"s{s}"] = {"published_kept_with_genhlth": b["published"]["kept"].get("genhlth"),
                        "lock_runs_valid_before_rounding": b["lock"]["valid_before_rounding"],
                        "lock_patients_with_run_valid_before_rounding": b["lock"]["patients_with_run_valid_before_rounding"],
                        "lock_coverage_x": b["lock"]["coverage_x"]}
    chk["genhlth_sentence"] = gen
    return chk


def main():
    if hashlib.sha256(PLAN.read_bytes()).hexdigest() != PLAN_SHA256:
        sys.exit("S-P4 plan hash mismatch")
    from depgraph.nodes import TIER
    import a2_domain as D
    roles = dict(TIER)
    roles_ckd = dict(D.ROLE)
    res = {"label": "POST HOC (S-P4), exploratory; preregistered verdicts unchanged", "plan_sha256": PLAN_SHA256,
           "written": datetime.now().strftime("%d/%m/%Y %H:%M"), "margin": MARGIN}
    W, covs, cohs = {}, {}, {}
    for tag in [f"s{s}" for s in MLP_SEEDS] + ["lr"]:
        W[tag], covs[tag], cohs[tag] = wachter_block(tag, roles)
    res["wachter"] = W
    pooled = {}
    for name, seeds in (("key_seeds_46_48_49", KEY_SEEDS), ("all_accepted_seeds", MLP_SEEDS)):
        parts = []
        for s in seeds:
            c = covs[f"s{s}"]
            if not all(m in c for m in ("route", "forced", "lockroute", "lock", "published")):
                continue
            parts.append(pd.DataFrame({"cluster": cohs[f"s{s}"]["test_pos"].to_numpy(),
                                       **{m: c[m].to_numpy() for m in ("published", "lock", "route", "forced", "lockroute")}}))
        if not parts:
            pooled[name] = {"status": "not reached"}
            continue
        df = pd.concat(parts, ignore_index=True)
        dg = cluster_boot_diff(df, "route", "forced")
        dr = cluster_boot_diff(df, "route", "lockroute")
        pooled[name] = {"n_seeds": len(parts), "units": int(len(df)),
                        "coverage": {m: float(df[m].mean()) for m in ("published", "lock", "route", "forced", "lockroute")},
                        "delta_G_route_minus_forced": dg | {"reading": reading(dg["ci95"])},
                        "delta_R_route_minus_lockroute": dr | {"reading": reading(dr["ci95"])}}
    res["pooled"] = pooled
    for tag in [f"s{s}" for s in MLP_SEEDS] + ["lr"]:
        c = covs[tag]
        if all(m in c for m in ("route", "forced")):
            n = len(c["route"])
            W[tag]["delta_G_coverage"] = (int(c["route"].sum()) - int(c["forced"].sum())) / n
        if all(m in c for m in ("route", "lockroute")):
            W[tag]["delta_R_coverage"] = (int(c["route"].sum()) - int(c["lockroute"].sum())) / n
    res["ckd"] = {cfg: ckd_block(cfg, roles_ckd) for cfg in ("ses_freeze", "frozen")}
    res["reviewer_checks"] = reviewer_checks(W)
    res["presentation_layer"] = presentation_layer(roles, roles_ckd)
    out = FL / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    (out / "forced_lever_results.json").write_text(json.dumps(res, indent=2, default=float) + "\n", encoding="utf-8")
    print(json.dumps(pooled, indent=1, default=float))


if __name__ == "__main__":
    main()
