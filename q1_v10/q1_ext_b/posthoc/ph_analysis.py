"""POST-HOC B-P1, step 3: per-seed and pooled results (plan sections 4-6), plus the AR/LR 99% addition.

Per accepted seed: the frozen `b_analysis` helpers (describe, movability_null, boot, q) and the same H4/H5 code as
b_analysis.main, with the decision rules reported as "rule met / rule not met / rule undecided" (descriptive, no
verdicts). Two-sided 95% and 99% intervals and the one-sided 99% bounds (1st / 99th percentiles of 2,000 bootstrap
means, fresh default_rng(20261111)).
Pooled: unit = (seed, test patient); cluster bootstrap over test patients (test index), 2,000 resamples,
default_rng(20261111), ratio of cluster sums; pooled movability null = frozen per-patient null with each unit as a
patient (descriptive).
Addition (plan section 6): AR/LR fully unactionable share, published, from the frozen extension B outputs; must
reproduce the reported point estimate and 95% interval before the 99% bounds are written.

Usage (p7-carla312 venv): python -I ph_analysis.py
Output: q1_ext_b_posthoc/analysis/posthoc_b_results.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ph_common as PH  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import b_analysis as BA  # noqa: E402
import b_common as C  # noqa: E402

D = C.stats()
LV = (0.95, 0.99)
REQ = BA.REQ


def rule(met, not_met):
    return "rule met" if met else ("rule not met" if not_met else "rule undecided")


def seed_block(seed, Xte, cols, span):
    W = PH.wachter_dir(seed)
    info = json.loads((W / "run_info.json").read_text(encoding="utf-8"))
    coh = pd.read_csv(PH.mlp_dir(seed) / "cohort.csv")
    pids = np.arange(len(coh))
    queries = Xte.iloc[coh["test_pos"].to_numpy()].reset_index(drop=True)
    x_by_pid = {i: queries.iloc[i].to_numpy(float) for i in pids}
    mv = pd.read_csv(W / "movability.csv").fillna({"movable": ""})
    movd = {int(r.pid): [f for f in r.movable.split(";") if f] for r in mv.itertuples()}
    block = {"label": PH.LABEL, "mlp_seed": seed, "cohort_n": len(pids),
             "model_info": json.loads((PH.mlp_dir(seed) / "model_info.json").read_text(encoding="utf-8")),
             "run_info": {k: v for k, v in info.items() if k != "patterns"}}
    block["model_info"].pop("train_loss_per_epoch", None)
    kept, per = {}, {}
    for mode in ("published", "lock", "route"):
        fk = W / f"kept_{mode}.csv"
        if not fk.exists() or info.get(f"status_{mode}") != "complete":
            block[mode] = {"status": info.get(f"status_{mode}", "not run")}
            continue
        kept[mode] = pd.read_csv(fk).fillna({"changed": ""})
        rows = pd.read_csv(W / f"rows_{mode}.csv").fillna({"changed": ""})
        if len(kept[mode]):  # B-P1b: a mode can have no kept output at all (empty frame)
            kept[mode]["point_key"] = kept[mode][[f"cf_{c}" for c in cols]].astype(str).agg("|".join, axis=1)
        d, per[mode], _ = BA.describe(kept[mode], pids, REQ, cols, x_by_pid, span)
        fr = rows[rows["feasible"]]
        d["runs"] = {"n_runs": int(len(rows)), "feasible_runs": int(len(fr)),
                     "valid_before_rounding": float(fr["valid_pre"].mean()),
                     "valid_after_rounding": float(fr["valid_post"].mean()),
                     "valid_after_given_before": float(fr.loc[fr["valid_pre"], "valid_post"].mean()) if fr["valid_pre"].any() else float("nan"),
                     "mean_iterations": float(fr["iters"].mean()), "share_capped_runs": float((~fr["valid_pre"]).mean())}
        d["kept_valid_before_rounding"] = float(kept[mode]["valid_pre"].mean()) if len(kept[mode]) else float("nan")
        d["cpu_hours"] = float(info.get(f"cpu_secs_{mode}", np.nan)) / 3600
        if mode == "route":
            d["change_sizes_route_supported"] = BA.change_sizes(kept[mode], x_by_pid, cols)
        block[mode] = d
    rules = {}
    unit = {"pid": pids, "test_index": coh["test_index"].to_numpy()}
    if "published" in kept and len(per["published"]):
        pp = per["published"]
        oa1, bs = BA.boot(pp["fully"].to_numpy(), LV)
        oa1["lower_one_sided_99"], oa1["upper_one_sided_99"] = BA.q(bs, 0.01), BA.q(bs, 0.99)
        oa1["patients_without_output"] = int(len(pids) - len(pp))
        nul = BA.movability_null(kept["published"], movd)
        lo1, hi1, p = oa1["lower_one_sided_99"], oa1["upper_one_sided_99"], nul["p"]
        rules["H4_rule"] = {"reading": rule(lo1 > BA.H4_FLOOR and p < 0.01, hi1 <= BA.H4_FLOOR or p >= 0.5),
                            "fully_unactionable": oa1, "movability_null": nul,
                            "component_i_lower99_gt_0.10": lo1 > BA.H4_FLOOR, "component_ii_p_lt_0.01": p < 0.01,
                            "reading_if_two_sided_99": rule(oa1["ci99"][0] > BA.H4_FLOOR and p < 0.01,
                                                            oa1["ci99"][1] <= BA.H4_FLOOR or p >= 0.5)}
        rules["dice_like_failure"] = rules["H4_rule"]["reading"] == "rule met"
    else:
        rules["H4_rule"] = {"reading": "not reached"}
        rules["dice_like_failure"] = None
    if "published" in kept and "lock" in kept:
        cnt = {m: kept[m].groupby("pid").size().reindex(pids).fillna(0).to_numpy() for m in ("published", "lock")}
        dd, bs = BA.boot((cnt["lock"] - cnt["published"]) / REQ, LV)
        dd["lower_one_sided_99"], dd["upper_one_sided_99"] = BA.q(bs, 0.01), BA.q(bs, 0.99)
        dd["published_valid_among_requested"] = float((cnt["published"] / REQ).mean())
        dd["lock_valid_among_requested"] = float((cnt["lock"] / REQ).mean())
        pv = dd["published_valid_among_requested"]
        dd["relative_loss"] = float((pv - dd["lock_valid_among_requested"]) / pv) if pv > 0 else float("nan")
        x = int((cnt["lock"] > 0).sum())
        lcov = x / len(pids)
        rules["H5_rule"] = {"reading": rule(dd["lower_one_sided_99"] > BA.H5_MARGIN and lcov >= 0.95,
                                            dd["upper_one_sided_99"] < BA.H5_MARGIN or lcov < 0.95),
                            "delta_valid_among_requested": dd, "lock_coverage_point": lcov, "lock_coverage_x": x,
                            "lock_coverage_cp95": D.clopper_pearson(x, len(pids), 0.95),
                            "lock_coverage_cp99": D.clopper_pearson(x, len(pids), 0.99),
                            "reading_if_two_sided_99": rule(dd["ci99"][0] > BA.H5_MARGIN and lcov >= 0.95,
                                                            dd["ci99"][1] < BA.H5_MARGIN or lcov < 0.95)}
        unit["n_pub"], unit["n_lock"] = cnt["published"], cnt["lock"]
    else:
        rules["H5_rule"] = {"reading": "not reached"}
    if "lock" in kept and "route" in kept:
        bl, br = per["lock"]["best"], per["route"]["best"]
        pair = sorted(set(bl.index) & set(br.index))
        eq, _ = BA.boot(bl.loc[pair].to_numpy() - br.loc[pair].to_numpy(), (0.95, 0.98))
        lo98, hi98 = eq.get("ci98", [np.nan, np.nan])
        rd = ("equivalent" if (lo98 > -BA.DELTA and hi98 < BA.DELTA) else
              "not equivalent" if (lo98 >= BA.DELTA or hi98 <= -BA.DELTA) else "undecided")
        rules["S_route_vs_lock_best_kept_cost_TOST"] = eq | {"delta": BA.DELTA, "reading": rd, "n_paired": len(pair)}
    block["rules_descriptive"] = rules
    fully = per["published"]["fully"] if "published" in per else pd.Series(dtype=float)
    unit_df = pd.DataFrame(unit)
    unit_df["fully"] = unit_df["pid"].map(fully)  # NaN = no kept published output
    pub = kept.get("published", pd.DataFrame(columns=["pid", "changed"]))
    return block, unit_df, pub, movd


def cluster_boot(values, clusters, levels=LV, B=2000, seed=20261111):
    """Ratio-of-sums cluster bootstrap: resample clusters (test patients) with all their units."""
    df = pd.DataFrame({"v": values, "c": clusters}).dropna()
    g = df.groupby("c")["v"].agg(["sum", "count"])
    S, N = g["sum"].to_numpy(), g["count"].to_numpy()
    rng = np.random.default_rng(seed)
    bs = np.empty(B)
    for b in range(B):
        i = rng.integers(0, len(S), len(S))
        bs[b] = S[i].sum() / N[i].sum()
    out = {"n_units": int(len(df)), "n_clusters": int(len(S)), "est": float(S.sum() / N.sum())}
    for lv in levels:
        a = (1 - lv) / 2
        out[f"ci{int(round(lv * 100))}"] = [float(np.quantile(bs, a)), float(np.quantile(bs, 1 - a))]
    out["lower_one_sided_99"], out["upper_one_sided_99"] = float(np.quantile(bs, 0.01)), float(np.quantile(bs, 0.99))
    return out


def spread(vals):
    v = [x for x in vals if x is not None and not (isinstance(x, float) and np.isnan(x))]
    if not v:
        return None
    return {"n_seeds": len(v), "median": float(np.median(v)), "min": float(np.min(v)), "max": float(np.max(v))}


def ar_addition(Xte, cols, span):
    """AR/LR fully unactionable share (published, secondary), 99% bounds (plan section 6)."""
    Wd = C.OUT / "ar_lr"
    ref = json.loads((C.OUT / "analysis" / "b_results.json").read_text(encoding="utf-8"))["ar"]["published"]["fully"]
    coh = pd.read_csv(C.OUT / "models" / "lr" / "cohort.csv")
    pids = np.arange(len(coh))
    queries = Xte.iloc[coh["test_pos"].to_numpy()].reset_index(drop=True)
    x_by_pid = {i: queries.iloc[i].to_numpy(float) for i in pids}
    o = pd.read_csv(Wd / "out_published.csv").fillna({"changed": ""})
    o = o[o["valid_post"]].copy()
    o["point_key"] = o[[f"cf_{c}" for c in cols]].astype(str).agg("|".join, axis=1)
    _, per, _ = BA.describe(o, pids, 5, cols, x_by_pid, span)
    r, bs = BA.boot(per["fully"].to_numpy(), LV)
    same = (r["n"] == ref["n"] and r["est"] == ref["est"] and r["ci95"] == ref["ci95"])
    if not same:
        sys.exit(f"AR addition: does not reproduce b_results.json ({r} vs {ref})")
    r["lower_one_sided_99"], r["upper_one_sided_99"] = BA.q(bs, 0.01), BA.q(bs, 0.99)
    return {"label": "ADDITION (12/11/2026, plan B-P1 section 6): secondary Actionable Recourse / LR, published mode, "
                     "fully unactionable share; 99% bounds added to the frozen extension B result; not part of B-P1's "
                     "question and not a primary result",
            "source": str(Wd / "out_published.csv"), "reproduces_b_results_point_and_ci95": same,
            "bootstrap": "percentile, 2,000 resamples of patients, default_rng(20261111) (C9)", **r}


def main():
    PH.check()
    C.below_normal()
    X, y, Xtr, Xte, ytr, yte = C.load_brfss()
    cols = list(X.columns)
    lo, span = C.ranges(cols)
    scr = json.loads((PH.OUT / "seed_screen.json").read_text(encoding="utf-8"))
    res = {"label": PH.LABEL, "plan": str(PH.PLAN), "plan_sha256": PH.PLAN_SHA256,
           "written": datetime.now().strftime("%d/%m/%Y %H:%M"),
           "seed_screen": {k: scr[k] for k in ("seeds_tried", "accepted", "n_tried", "stop_reason", "harness_check_seed42")},
           "shortfall": max(0, PH.MAX_ACCEPTED - len(scr["accepted"]))}
    seeds = scr["accepted"]
    per_seed, units, pubs, movs = {}, [], [], {}
    for s in seeds:
        b, u, pub, movd = seed_block(s, Xte, cols, span)
        per_seed[str(s)] = b
        u["mlp_seed"] = s
        units.append(u)
        pub = pub.copy()
        pub["pid"] = s * 1000 + pub["pid"].astype(int)
        pubs.append(pub)
        movs.update({s * 1000 + k: v for k, v in movd.items()})
    res["per_seed"] = per_seed
    if not seeds:
        res["pooled"] = {"status": "not reached post hoc (no accepted seed)"}
    else:
        U = pd.concat(units, ignore_index=True)
        pooled = {"label": PH.LABEL + "; units (seed, patient) are clustered by test patient",
                  "seeds": seeds, "n_units": int(len(U)), "n_test_patients": int(U["test_index"].nunique())}
        pooled["fully_unactionable"] = cluster_boot(U["fully"].to_numpy(), U["test_index"].to_numpy())
        pooled["fully_unactionable"]["units_without_output"] = int(U["fully"].isna().sum())
        if "n_lock" in U:
            ok = U.dropna(subset=["n_lock"])
            pooled["delta_valid_among_requested"] = cluster_boot(((ok["n_lock"] - ok["n_pub"]) / REQ).to_numpy(),
                                                                 ok["test_index"].to_numpy())
            pooled["lock_coverage"] = cluster_boot((ok["n_lock"] > 0).astype(float).to_numpy(), ok["test_index"].to_numpy())
        P = pd.concat(pubs, ignore_index=True)
        if len(P):
            pooled["movability_null_units_as_patients"] = BA.movability_null(P, movs) | {
                "note": "descriptive only: units are clustered by test patient"}
        rd = [per_seed[str(s)]["rules_descriptive"] for s in seeds]
        pooled["seeds_meeting_H4_rule"] = sum(r["H4_rule"]["reading"] == "rule met" for r in rd)
        pooled["seeds_meeting_H5_rule"] = sum(r["H5_rule"]["reading"] == "rule met" for r in rd)
        pooled["H4_rule_readings"] = {str(s): r["H4_rule"]["reading"] for s, r in zip(seeds, rd)}
        pooled["H5_rule_readings"] = {str(s): r["H5_rule"]["reading"] for s, r in zip(seeds, rd)}
        pooled["per_seed_spread"] = {
            "fully_unactionable": spread([r["H4_rule"].get("fully_unactionable", {}).get("est") for r in rd]),
            "movability_p": spread([r["H4_rule"].get("movability_null", {}).get("p") for r in rd]),
            "delta_valid_among_requested": spread([r["H5_rule"].get("delta_valid_among_requested", {}).get("est") for r in rd]),
            "lock_coverage": spread([r["H5_rule"].get("lock_coverage_point") for r in rd])}
        res["pooled"] = pooled
    res["addition_ar_lr_fully_unactionable_99"] = ar_addition(Xte, cols, span)
    out = PH.OUT / "analysis" / "posthoc_b_results.json"
    C.write_json(out, res)
    brief = {"accepted": seeds, "per_seed": {s: {"H4": b["rules_descriptive"]["H4_rule"]["reading"],
                                                 "H5": b["rules_descriptive"]["H5_rule"]["reading"]}
                                             for s, b in per_seed.items()},
             "ar_addition": {k: res["addition_ar_lr_fully_unactionable_99"][k]
                             for k in ("est", "ci95", "ci99", "lower_one_sided_99", "upper_one_sided_99")}}
    print(json.dumps(brief, indent=1, default=float))


if __name__ == "__main__":
    main()
