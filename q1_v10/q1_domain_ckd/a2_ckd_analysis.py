"""P7 Q1 step A2: CKD primary decisions H1-H3 and the secondaries computed from the same runs (prereg v3 4.7, 4.8, 8).

Reads only the per-counterfactual files written by a2_ckd_runs.py. Decision rules exactly as prereg v3:
  H1  (i) one-sided 99% lower bootstrap bound of O-A1 > 0.10 and (ii) movability-null p < 0.01;
      not supported if the 99% upper bound of O-A1 <= 0.10 or p >= 0.5; undecided otherwise.
  H2  99% lower bound of O-A3 (lock - published valid among requested) > -0.05 and lock coverage >= 0.95 (point);
      not supported if the 99% upper bound < -0.05 or coverage < 0.95; undecided otherwise.
  H3  TOST alpha 0.01: 98% percentile interval of mean O-A5 inside (-0.05, 0.05) -> supported; lower >= 0.05 or
      upper <= -0.05 -> not supported; otherwise undecided; not testable if the graph is degenerate; flagged if
      near-degenerate (computed in a2_ckd_runs.py from the cohort, before any generator ran).
One-sided 99% bounds are the 1st / 99th percentiles of the 2,000 bootstrap means (clarification C9); the two-sided
99% interval is also reported. Bootstrap: 2,000 patient resamples, seed 20261111. Patient proportions:
Clopper-Pearson (99% for decisions, 95% for secondaries). Numbers in the note are truncated to 4 decimals.

Usage (P4 venv): python -I a2_ckd_analysis.py --cohort main|less_exposed
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import a2_domain as D  # noqa: E402
from q1_common import check_prereg, write_json  # noqa: E402

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


def kappa(a, b):
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    po = float(np.mean(a == b))
    pa, pb = a.mean(), b.mean()
    pe = pa * pb + (1 - pa) * (1 - pb)
    return po, (np.nan if pe >= 1 else (po - pe) / (1 - pe))


def load(cohort):
    R = D.OUT / f"a2_runs_{cohort}"
    info = json.loads((R / "run_info.json").read_text(encoding="utf-8"))
    coh = pd.read_csv(R / "cohort.csv")
    mov = pd.read_csv(R / "movability.csv").fillna({"movable": ""})
    dice = {m: pd.concat([pd.read_csv(R / f"dice_{m}_seed{s}.csv") for s in SEEDS], ignore_index=True)
            for m in ("published", "lock", "route")}
    for m in dice:
        dice[m]["changed"] = dice[m]["changed"].fillna("")
    exh = pd.read_csv(R / "exhaustive.csv")
    exh["changed"] = exh["changed"].fillna("")
    return info, coh, mov, dice, exh


def sets(series):
    return [set(s.split(";")) - {""} for s in series]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", choices=["main", "less_exposed"], required=True)
    a = ap.parse_args()
    check_prereg()
    info, coh, mov, dice, exh = load(a.cohort)
    (D.OUT / "a2_analysis").mkdir(parents=True, exist_ok=True)
    n = len(coh)
    pids = coh["pid"].to_numpy()
    KD, AD = D.kdigo_edges(), D.ada_edges()
    E_K, E_A = D.edge_set(KD), D.edge_set(AD)
    res = {"cohort": a.cohort, "written": datetime.now().strftime("%d/%m/%Y %H:%M"), "n_cohort": n,
           "test_auc": info["test_auc"], "eligible": info["eligible_p_ge_0.5"],
           "near_degenerate_check": info["near_degenerate_check"],
           "pre_generator_single_nonindicator_flip_share": info["pre_generator_single_nonindicator_flip_share"],
           "kdigo_edges_items": sorted(E_K), "ada_edges_items": sorted(E_A)}
    # S1 as a patient proportion with a Clopper-Pearson interval
    k1 = int(round(info["pre_generator_single_nonindicator_flip_share"] * n))
    res["pre_generator_single_nonindicator_flip"] = {"x": k1, "n": n, "cp95": D.clopper_pearson(k1, n, 0.95)}

    # ---------------------------------------------------------------- DiCE published: O-A1, O-share, O-A2
    dp = dice["published"].copy()
    S_dp = sets(dp["changed"])
    cl = [D.classify(s, E_K) for s in S_dp]
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
    osh, _ = boot_summary(per["oshare"].to_numpy())
    res["O_share_dice_published"] = osh
    tch, _ = boot_summary(per["touch"].to_numpy())
    res["touch_share_dice_published"] = tch

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
                                   "max_subsets_per_patient": int(max(sizes)),
                                   "changes_outside_movable_set": int(outside)}

    lo, hi = oa1["lower_one_sided_99"], oa1["upper_one_sided_99"]
    if lo > H1_FLOOR and p < 0.01:
        h1 = "supported"
    elif hi <= H1_FLOOR or p >= 0.5:
        h1 = "not supported"
    else:
        h1 = "undecided"
    res["H1"] = {"verdict": h1, "component_i_replication_lower99_gt_0.10": lo > H1_FLOOR,
                 "component_ii_p_lt_0.01": p < 0.01,
                 "verdict_if_two_sided_99": ("supported" if oa1["ci99"][0] > H1_FLOOR and p < 0.01 else
                                             "not supported" if oa1["ci99"][1] <= H1_FLOOR or p >= 0.5 else "undecided")}

    # ---------------------------------------------------------------- O-A3 / H2 and route cost (DiCE)
    def valreq(m):
        v = dice[m].groupby("pid")["valid"].sum().reindex(pids).fillna(0).to_numpy()
        return v / REQUESTED

    vr = {m: valreq(m) for m in dice}
    cov = {m: int((dice[m][dice[m]["valid"] == 1].groupby("pid").size().reindex(pids).fillna(0) > 0).sum()) for m in dice}
    ret_cov = {m: int((dice[m].groupby("pid").size().reindex(pids).fillna(0) > 0).sum()) for m in dice}
    oa3, bs3 = boot_summary(vr["lock"] - vr["published"], (0.95, 0.99))
    oa3["lower_one_sided_99"], oa3["upper_one_sided_99"] = q(bs3, 0.01), q(bs3, 0.99)
    oa3["published_valid_among_requested"] = float(vr["published"].mean())
    oa3["lock_valid_among_requested"] = float(vr["lock"].mean())
    oa3["relative_loss"] = float((vr["published"].mean() - vr["lock"].mean()) / vr["published"].mean())
    res["O_A3_valid_among_requested_lock_minus_published"] = oa3
    res["coverage_dice"] = {m: {"x_valid": cov[m], "x_returned": ret_cov[m], "n": n, "share": cov[m] / n,
                                "cp99": D.clopper_pearson(cov[m], n, 0.99), "cp95": D.clopper_pearson(cov[m], n, 0.95)}
                            for m in dice}
    lcov = cov["lock"] / n
    if oa3["lower_one_sided_99"] > H2_MARGIN and lcov >= 0.95:
        h2 = "supported"
    elif oa3["upper_one_sided_99"] < H2_MARGIN or lcov < 0.95:
        h2 = "not supported"
    else:
        h2 = "undecided"
    res["H2"] = {"verdict": h2, "lock_coverage_point": lcov,
                 "verdict_if_two_sided_99": ("supported" if oa3["ci99"][0] > H2_MARGIN and lcov >= 0.95 else
                                             "not supported" if oa3["ci99"][1] < H2_MARGIN or lcov < 0.95 else "undecided")}
    rc, _ = boot_summary(vr["route"] - vr["published"])
    rc["route_valid_among_requested"] = float(vr["route"].mean())
    R = D.OUT / f"a2_runs_{a.cohort}"
    st = pd.concat([pd.read_csv(R / f"dice_route_seed{s}_status.csv") for s in SEEDS])
    rc["mean_rounds"] = float(st["rounds"].mean())
    res["route_cost_dice_route_minus_published"] = rc

    # ---------------------------------------------------------------- exhaustive: O-A5 / H3, O-A4, costs
    best = exh[exh["round"] == 0].set_index(["mode", "pid"])
    exc = {}
    for m in ("published", "lock", "route", "capped"):
        b = best.loc[m] if m in best.index.get_level_values(0) else pd.DataFrame(columns=["n_changes", "dist"])
        x = int(len(b))
        kk, _ = boot_summary(b["n_changes"].to_numpy()) if x else ({"est": np.nan}, None)
        dd, _ = boot_summary(b["dist"].to_numpy()) if x else ({"est": np.nan}, None)
        exc[m] = {"coverage_x": x, "n": n, "coverage": x / n, "cp95": D.clopper_pearson(x, n, 0.95),
                  "best_changes": kk, "best_dist": dd}
    bl, br = best.loc["lock"], best.loc["route"]
    pair = sorted(set(bl.index) & set(br.index))
    d5 = bl.loc[pair, "dist"].to_numpy() - br.loc[pair, "dist"].to_numpy()
    oa5, bs5 = boot_summary(d5, (0.95, 0.98))
    res["O_A5_dist_lock_minus_route_exhaustive"] = oa5 | {"n_route_only": len(set(br.index) - set(bl.index)),
                                                          "n_lock_only": len(set(bl.index) - set(br.index)),
                                                          "share_exactly_zero": float(np.mean(np.abs(d5) < 1e-12))}
    nd = info["near_degenerate_check"]
    lo5, hi5 = oa5["ci98"]
    if nd["degenerate"]:
        h3 = "not testable: degenerate graph"
    elif -DELTA < lo5 and hi5 < DELTA:
        h3 = "supported (equivalent)"
    elif lo5 >= DELTA or hi5 <= -DELTA:
        h3 = "not supported (not equivalent)"
    else:
        h3 = "undecided"
    res["H3"] = {"verdict": h3, "near_degenerate_flag": nd["near_degenerate"],
                 "reading": ("equivalence not counted as evidence about the graph (near-degenerate)"
                             if nd["near_degenerate"] else "graph not near-degenerate; verdict read as stated")}
    kl, kr = bl.loc[pair, "n_changes"].to_numpy(), br.loc[pair, "n_changes"].to_numpy()
    dl, dr = bl.loc[pair, "dist"].to_numpy(), br.loc[pair, "dist"].to_numpy()
    better = (kr < kl) | ((kr == kl) & (dr < dl - 1e-12))
    worse = (kr > kl) | ((kr == kl) & (dr > dl + 1e-12))
    xb = int(better.sum())
    res["O_A4_route_strictly_better_than_lock"] = {"x": xb, "n_pairs": len(pair), "share": xb / len(pair),
                                                    "cp95": D.clopper_pearson(xb, len(pair), 0.95)}
    res["exhaustive_costs"] = exc
    for m in ("lock", "route"):
        bm = best.loc[m]
        pp = sorted(set(bm.index) & set(best.loc["published"].index))
        for met in ("n_changes", "dist"):
            s, _ = boot_summary(bm.loc[pp, met].to_numpy() - best.loc["published"].loc[pp, met].to_numpy())
            res["exhaustive_costs"][m][f"{met}_minus_published"] = s
    bc = best.loc["capped"]
    pp = sorted(set(bc.index) & set(br.index))
    s, _ = boot_summary(bc.loc[pp, "dist"].to_numpy() - br.loc[pp, "dist"].to_numpy()) if pp else ({}, None)
    res["exhaustive_costs"]["capped"]["dist_minus_route"] = s

    # ---------------------------------------------------------------- software checks (Lemma 1, Lemma 3, depgraph)
    sc = {}
    for m, df in (("dice_route", dice["route"]), ("exh_route", exh[exh["mode"] == "route"]),
                  ("exh_capped", exh[exh["mode"] == "capped"])):
        sc[f"{m}_leaking_cfs"] = int(sum(D.classify(s, E_K)["leaks"] for s in sets(df["changed"])))
    for m, df in (("dice_lock", dice["lock"]), ("exh_lock", exh[exh["mode"] == "lock"])):
        sc[f"{m}_indicator_touching_cfs"] = int(sum(D.classify(s, E_K)["touches"] for s in sets(df["changed"])))
    sc["lemma3_route_worse_than_lock_patients"] = int(worse.sum())
    from depgraph import audit as A
    all_sets = sets(pd.concat([dp["changed"], exh[exh["mode"] == "published"]["changed"]]))
    sc["depgraph_ada_k1_disagreements"] = int(sum(D.classify(s, E_A)["leaks"] != A.classify(s, reading="narrow", rule="edge")["unsupported"]
                                                  for s in all_sets))
    res["software_checks"] = sc

    # ---------------------------------------------------------------- leakage under all readings (published)
    lab = dict(zip(coh["pid"], coh["CKD_label"]))
    E_in = {True: D.edge_set(KD, in_scope_ckd=True), False: D.edge_set(KD, in_scope_ckd=False)}
    readings = {"primary_kdigo_k1": (E_K, 1, False), "kdigo_k2_permissive": (E_K, 2, False),
                "kdigo_k2_strict": (E_K, 2, True), "union_kdigo_ada_k1": (E_K | E_A, 1, False),
                "union_kdigo_ada_k2_permissive": (E_K | E_A, 2, False), "union_kdigo_ada_k2_strict": (E_K | E_A, 2, True),
                "other_domain_ada_k1": (E_A, 1, False),
                "graded_only_kdigo_k1": (D.edge_set(KD, graded_only=True), 1, False), "in_scope_kdigo_k1": None}
    leak = {}
    for gen, df in (("dice_random", dp), ("exhaustive", exh[exh["mode"] == "published"])):
        leak[gen] = {}
        S = sets(df["changed"])
        for name, spec in readings.items():
            if spec is None:
                lk = [D.classify(s, E_in[bool(lab[p_])])["leaks"] for s, p_ in zip(S, df["pid"])]
            else:
                lk = [D.classify(s, spec[0], spec[1], spec[2])["leaks"] for s in S]
            t = pd.Series(lk, index=df.index).groupby(df["pid"]).mean().reindex(pids).dropna()
            s_, _ = boot_summary(t.to_numpy())
            leak[gen][name] = s_ | {"cf_level_share": float(np.mean(lk))}
        fu = pd.Series([D.classify(s, E_K)["fully_unactionable"] for s in S], index=df.index).groupby(df["pid"]).mean()
        to = pd.Series([D.classify(s, E_K)["touches"] for s in S], index=df.index).groupby(df["pid"]).mean()
        leak[gen]["fully_unactionable"], _ = boot_summary(fu.to_numpy())
        leak[gen]["touch"], _ = boot_summary(to.to_numpy())
    res["leakage_published"] = leak

    # ---------------------------------------------------------------- change sizes and capped share
    feats = D.FEATURES
    xq = coh.set_index("pid")[[f"x_{f}" for f in feats]]
    cs_rows = []
    for src, df in (("dice_published", dp), ("dice_route", dice["route"]),
                    ("exh_published", exh[exh["mode"] == "published"]), ("exh_route", exh[exh["mode"] == "route"])):
        for r in df.itertuples():
            S = set(r.changed.split(";")) - {""}
            for v in sorted(S & D.INDICATORS):
                levs = D.supporting_levers(v, S, E_K)
                if not levs:
                    continue
                before, after = float(xq.loc[r.pid, f"x_{v}"]), float(getattr(r, f"cf_{v}"))
                cs_rows.append({"source": src, "indicator": v, "levers": "+".join(levs), "pid": r.pid,
                                "before": before, "after": after, "steps": D.indicator_step(v, before, after),
                                "within_cap": D.indicator_step(v, before, after) <= len(levs)})
    cs = pd.DataFrame(cs_rows)
    cs.to_csv(D.OUT / "a2_analysis" / f"change_sizes_{a.cohort}.csv", index=False) if len(cs) else None
    sizes = {}
    if len(cs):
        for (src, v, lv), g in cs.groupby(["source", "indicator", "levers"]):
            sizes[f"{src}|{v}|{lv}"] = {"n": int(len(g)), "steps_distribution": {str(k): int(c) for k, c in sorted(Counter(g["steps"]).items())},
                                        "share_within_cap": float(g["within_cap"].mean()),
                                        "raw_change_mean": float((g["after"] - g["before"]).mean())}
    res["change_sizes_supported_indicator_moves"] = sizes
    dr_ = dice["route"]
    capped = []
    for r in dr_.itertuples():
        S = set(r.changed.split(";")) - {""}
        before = {f: float(xq.loc[r.pid, f"x_{f}"]) for f in feats}
        after = {f: float(getattr(r, f"cf_{f}")) for f in feats}
        capped.append(D.capped_ok(S, before, after, E_K))
    res["dice_route_share_meeting_cap"] = float(np.mean(capped)) if capped else None

    # ---------------------------------------------------------------- A-Q4 cross-guideline agreement
    aq = {}
    pools = {"dice_random": dp, "exhaustive": exh[exh["mode"] == "published"]}
    pools["all_generators"] = pd.concat(list(pools.values()), ignore_index=True)
    for gen, df in pools.items():
        S = sets(df["changed"])
        keep = [i for i, s in enumerate(S) if s & D.INDICATORS]
        sub = df.iloc[keep]
        vk = np.array([not D.classify(S[i], E_K)["leaks"] for i in keep])
        va = np.array([not D.classify(S[i], E_A)["leaks"] for i in keep])
        po, kp = kappa(vk, va)
        rng = np.random.default_rng(20261111)
        gp = sub["pid"].to_numpy()
        up = np.unique(gp)
        rows_of = {p_: np.where(gp == p_)[0] for p_ in up}
        bpo, bk = [], []
        for _ in range(2000):
            ii = np.concatenate([rows_of[p_] for p_ in rng.choice(up, len(up), replace=True)])
            a_, b_ = kappa(vk[ii], va[ii])
            bpo.append(a_)
            bk.append(b_)
        reading = "routes carry across the two guidelines" if po >= 0.80 else ("guideline-specific" if po < 0.60 else "partial")
        aq[gen] = {"n_cf": int(len(keep)), "n_patients": int(len(up)), "raw_agreement": po,
                   "raw_agreement_ci95": [float(np.nanquantile(bpo, .025)), float(np.nanquantile(bpo, .975))],
                   "kappa": kp, "kappa_ci95": [float(np.nanquantile(bk, .025)), float(np.nanquantile(bk, .975))],
                   "supported_kdigo": float(vk.mean()), "supported_ada": float(va.mean()), "reading": reading}
    res["A_Q4_cross_guideline_agreement"] = aq

    # ---------------------------------------------------------------- per cycle and distinct CFs
    cyc = dict(zip(coh["pid"], coh["Cycle"]))
    pc = {}
    for c in (0, 1):
        sub = per[[cyc[int(p_)] == c for p_ in per.index]]
        if len(sub):
            f_, _ = boot_summary(sub["fully"].to_numpy())
            o_, _ = boot_summary(sub["oshare"].to_numpy())
            pc[{0: "2017-2020", 1: "2021-2023"}[c]] = {"O_A1": f_, "O_share": o_}
    res["per_cycle_dice_published"] = pc
    vals = dp[[f"cf_{f}" for f in feats]].round(6).astype(str).agg("|".join, axis=1)
    dist_cf = vals.groupby(dp["pid"]).nunique()
    res["distinct_cfs_per_patient_dice_published"], _ = boot_summary(dist_cf.to_numpy())

    outd = D.OUT / "a2_analysis"
    outd.mkdir(parents=True, exist_ok=True)
    write_json(outd / f"results_{a.cohort}.json", res)
    per.to_csv(outd / f"per_patient_dice_published_{a.cohort}.csv")
    print(json.dumps({k: res[k] for k in ("H1", "H2", "H3")}, indent=1))


if __name__ == "__main__":
    main()
