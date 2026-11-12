"""P7 Q1 step A2-HTN: decisions H1-HTN to H3-HTN and the secondaries from the same runs (addendum HTN v3, 7, 8).

Decision rules copied from the frozen CKD a2_ckd_analysis.py (v3 H1-H3):
  H1 (i) one-sided 99% lower bootstrap bound of O-A1 > 0.10 and (ii) movability-null p < 0.01; not supported if the
     upper bound <= 0.10 or p >= 0.5; undecided otherwise.
  H2 one-sided 99% lower bound of O-A3 > -0.05 and lock coverage >= 0.95; not supported if upper bound < -0.05 or
     coverage < 0.95; undecided otherwise.
  H3 not reached when there is no agreed graph (recall gate failed, addendum 5.4); otherwise TOST at alpha 0.01 with
     the degenerate, near-degenerate and 'equivalent, uninformative' readings of addendum 7.3.
Bootstrap 2,000 patient resamples, seed 20261111; Clopper-Pearson for proportions.
Usage (P7 venv): python -I a2_htn_analysis.py --variant main
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(HERE))
sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import a2_domain_htn as D  # noqa: E402
from htn_common import check_prereg, write_json  # noqa: E402

SEEDS = [42, 123, 2024, 7, 31337]
REQUESTED = 5 * len(SEEDS)
DELTA, H2_MARGIN, H1_FLOOR = 0.05, -0.05, 0.10


def q(bs, p):
    return float(np.quantile(bs, p))


def boot_summary(x, levels=(0.95,)):
    x = np.asarray(x, dtype=float)
    bs = D.boot_means(x)
    out = {"n": int(len(x)), "est": float(np.mean(x))}
    for lv in levels:
        a = (1 - lv) / 2
        out[f"ci{int(lv * 100)}"] = [q(bs, a), q(bs, 1 - a)]
    return out, bs


def sets(series):
    return [set(s.split(";")) - {""} for s in series]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", required=True)
    a = ap.parse_args()
    check_prereg()
    R = D.OUT / f"a2_runs_{a.variant}"
    info = json.loads((R / "run_info.json").read_text(encoding="utf-8"))
    res = {"variant": a.variant, "written": datetime.now().strftime("%d/%m/%Y %H:%M"), "target": info["target"],
           "n_analytic": info["n_analytic"], "test_auc": info["test_auc"], "eligible": info["eligible_p_ge_0.5"],
           "r_imm_applied": info["r_imm_applied"], "aha_agreed_graph": info.get("aha_agreed_graph")}
    if info.get("status", "").startswith("NOT REACHED"):
        res["status"] = info["status"]
        write_json(D.OUT / "a2_analysis" / f"results_{a.variant}.json", res)
        print(res["status"])
        return
    coh = pd.read_csv(R / "cohort.csv")
    mov = pd.read_csv(R / "movability.csv").fillna({"movable": ""})
    graph = info.get("aha_agreed_graph") == "available"
    modes = ("published", "lock", "route") if graph else ("published", "lock")
    dice = {m: pd.concat([pd.read_csv(R / f"dice_{m}_seed{s}.csv") for s in SEEDS], ignore_index=True) for m in modes}
    for m in dice:
        dice[m]["changed"] = dice[m]["changed"].fillna("")
    exh = pd.read_csv(R / "exhaustive.csv")
    exh["changed"] = exh["changed"].fillna("")
    n = len(coh)
    pids = coh["pid"].to_numpy()
    E_A = D.edge_set(D.aha_edges())
    E_K, E_D = D.edge_set(D.kdigo_edges()), D.edge_set(D.ada_edges())
    res.update({"n_cohort": n, "near_degenerate_check": info["near_degenerate_check"],
                "aha_edges_items": sorted(E_A), "kdigo_edges_items": sorted(E_K), "ada_edges_items": sorted(E_D)})
    k1 = int(round(info["pre_generator_single_nonindicator_flip_share"] * n))
    res["S1_single_nonindicator_flip"] = {"x": k1, "n": n, "share": k1 / n, "cp95": D.clopper_pearson(k1, n, 0.95)}

    # ---- O-A1, O-share, O-A2 (DiCE published)
    dp = dice["published"].copy()
    cl = [D.classify(s, E_A) for s in sets(dp["changed"])]
    dp["fully"] = [c["fully_unactionable"] for c in cl]
    dp["touch"] = [c["touches"] for c in cl]
    dp["n_ind"] = [c["n_indicator_changes"] for c in cl]
    per = dp.groupby("pid").agg(ret=("valid", "size"), fully=("fully", "mean"), touch=("touch", "mean"),
                                ind=("n_ind", "sum"), chg=("n_changes", "sum")).reindex(pids)
    has = per["ret"].notna() & (per["ret"] > 0)
    per = per[has]
    per["oshare"] = np.where(per["chg"] > 0, per["ind"] / per["chg"].where(per["chg"] > 0, 1), 0.0)
    oa1, bs1 = boot_summary(per["fully"].to_numpy(), (0.95, 0.99))
    oa1["lower_one_sided_99"], oa1["upper_one_sided_99"] = q(bs1, 0.01), q(bs1, 0.99)
    oa1["patients_without_cf"] = int(n - has.sum())
    res["O_A1_fully_unactionable_dice_published"] = oa1
    res["O_share_dice_published"], _ = boot_summary(per["oshare"].to_numpy())
    res["touch_share_dice_published"], _ = boot_summary(per["touch"].to_numpy())
    movd = {int(r.pid): [f for f in r.movable.split(";") if f] for r in mov.itertuples()}
    observed, nulls, outside, sizes = [], [], 0, []
    for pid, g in dp.groupby("pid"):
        cnt = Counter(f for s in sets(g["changed"]) for f in s)
        M = movd[int(pid)]
        outside += sum(v for f, v in cnt.items() if f not in M)
        n_ind = sum(f in D.INDICATORS for f in M)
        observed.append(D.oshare(cnt, [f for f in cnt if f in D.INDICATORS]))
        nulls.append(D.patient_null(cnt, M, n_ind))
        sizes.append(len(nulls[-1]))
    T, p, n_ge = D.movability_null_p(observed, nulls, draws=100_000, seed=20261111)
    res["O_A2_movability_null"] = {"T_mean_oshare": T, "null_mean_of_means": float(np.mean([v.mean() for v in nulls])),
                                   "p": p, "draws": 100_000, "n_draws_ge": n_ge, "n_patients": len(observed),
                                   "max_subsets_per_patient": int(max(sizes)), "changes_outside_movable_set": int(outside)}
    lo, hi = oa1["lower_one_sided_99"], oa1["upper_one_sided_99"]
    h1 = "supported" if (lo > H1_FLOOR and p < 0.01) else ("not supported" if (hi <= H1_FLOOR or p >= 0.5) else "undecided")
    res["H1"] = {"verdict": h1, "component_i_lower99_gt_0.10": lo > H1_FLOOR, "component_ii_p_lt_0.01": p < 0.01}

    # ---- O-A3 / H2
    def valreq(m):
        return dice[m].groupby("pid")["valid"].sum().reindex(pids).fillna(0).to_numpy() / REQUESTED
    vr = {m: valreq(m) for m in dice}
    cov = {m: int((dice[m][dice[m]["valid"] == 1].groupby("pid").size().reindex(pids).fillna(0) > 0).sum()) for m in dice}
    oa3, bs3 = boot_summary(vr["lock"] - vr["published"], (0.95, 0.99))
    oa3["lower_one_sided_99"], oa3["upper_one_sided_99"] = q(bs3, 0.01), q(bs3, 0.99)
    oa3["published_valid_among_requested"] = float(vr["published"].mean())
    oa3["lock_valid_among_requested"] = float(vr["lock"].mean())
    res["O_A3_valid_among_requested_lock_minus_published"] = oa3
    res["coverage_dice"] = {m: {"x_valid": cov[m], "n": n, "share": cov[m] / n, "cp99": D.clopper_pearson(cov[m], n, 0.99)}
                            for m in dice}
    lcov = cov["lock"] / n
    h2 = ("supported" if (oa3["lower_one_sided_99"] > H2_MARGIN and lcov >= 0.95) else
          "not supported" if (oa3["upper_one_sided_99"] < H2_MARGIN or lcov < 0.95) else "undecided")
    res["H2"] = {"verdict": h2, "lock_coverage_point": lcov}

    # ---- exhaustive costs; H3
    best = exh[exh["round"] == 0].set_index(["mode", "pid"])
    exc = {}
    for m in sorted(set(exh["mode"])):
        b = best.loc[m]
        x = int(len(b))
        exc[m] = {"coverage_x": x, "n": n, "coverage": x / n, "cp95": D.clopper_pearson(x, n, 0.95),
                  "best_changes": boot_summary(b["n_changes"].to_numpy())[0], "best_dist": boot_summary(b["dist"].to_numpy())[0]}
    bl, bp = best.loc["lock"], best.loc["published"]
    pp = sorted(set(bl.index) & set(bp.index))
    exc["lock"]["dist_minus_published"], _ = boot_summary(bl.loc[pp, "dist"].to_numpy() - bp.loc[pp, "dist"].to_numpy())
    res["exhaustive_costs"] = exc
    if not graph:
        res["H3"] = {"verdict": "not reached", "reason": "extractor B (Qwen2.5-72B) failed the recall gate; no fallback "
                     "(addendum 5.4): the HTN agreed graph, H3-HTN and A-Q4-HTN are not reached"}
        res["A_Q4"] = "not reached"
    else:  # not used in this run; kept for completeness of the decision rule
        res["H3"] = {"verdict": "not computed in this script version"}

    # ---- leakage under the readings that do not need the AHA graph (secondary)
    leak = {}
    for gen, df in (("dice_random", dp), ("exhaustive", exh[exh["mode"] == "published"])):
        S = sets(df["changed"])
        leak[gen] = {}
        for name, Ex in (("kdigo_k1", E_K), ("ada_k1", E_D), ("union_kdigo_ada_k1", E_K | E_D)):
            lk = [D.classify(s, Ex)["leaks"] for s in S]
            t = pd.Series(lk, index=df.index).groupby(df["pid"]).mean().reindex(pids).dropna()
            leak[gen][name] = boot_summary(t.to_numpy())[0] | {"cf_level_share": float(np.mean(lk))}
        fu = pd.Series([D.classify(s, E_A)["fully_unactionable"] for s in S], index=df.index).groupby(df["pid"]).mean()
        leak[gen]["fully_unactionable"] = boot_summary(fu.to_numpy())[0]
    res["leakage_published_other_authorities"] = leak

    # ---- per cycle, distinct
    cyc = dict(zip(coh["pid"], coh["Cycle"]))
    pc = {}
    for c in (0, 1):
        sub = per[[cyc[int(p_)] == c for p_ in per.index]]
        if len(sub):
            pc[{0: "2017-2020", 1: "2021-2023"}[c]] = {"O_A1": boot_summary(sub["fully"].to_numpy())[0],
                                                     "O_share": boot_summary(sub["oshare"].to_numpy())[0]}
    res["per_cycle_dice_published"] = pc
    feats = info["features_in_model_order"]
    vals = dp[[f"cf_{f}" for f in feats]].round(6).astype(str).agg("|".join, axis=1)
    res["distinct_cfs_per_patient_dice_published"], _ = boot_summary(vals.groupby(dp["pid"]).nunique().to_numpy())
    chg_counts = Counter(f for s in sets(dp["changed"]) for f in s)
    res["feature_change_counts_dice_published"] = dict(chg_counts.most_common())
    sc = {"dice_lock_indicator_touching_cfs": int(sum(D.classify(s, E_A)["touches"] for s in sets(dice["lock"]["changed"]))),
          "exh_lock_indicator_touching_cfs": int(sum(D.classify(s, E_A)["touches"] for s in sets(exh[exh["mode"] == "lock"]["changed"]))),
          "changes_on_r_imm_features": int(sum(chg_counts.get(f, 0) for f in ("Income", "Education", "AnyHealthcare")))}
    res["software_checks"] = sc
    outd = D.OUT / "a2_analysis"
    outd.mkdir(parents=True, exist_ok=True)
    write_json(outd / f"results_{a.variant}.json", res)
    per.to_csv(outd / f"per_patient_dice_published_{a.variant}.csv")
    print(json.dumps({k: res[k] for k in ("H1", "H2", "H3")}, indent=1))


if __name__ == "__main__":
    main()
