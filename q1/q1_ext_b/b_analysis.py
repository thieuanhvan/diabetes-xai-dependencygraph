"""Extension B decisions H4, H5 and the secondaries (prereg v3 5.5, 8), from the per-run files only.

H4 (Wachter on MLP, published mode): supported if the one-sided 99% lower bootstrap bound of the fully
   unactionable share > 0.10 AND the per-patient movability null gives p < 0.01; not supported if the 99% upper
   bound <= 0.10 or p >= 0.5; undecided otherwise (as H1; intersection-union).
H5 (Wachter on MLP, lock minus published, both with P restarts): supported if the one-sided 99% lower bound of the
   change in valid among requested > -0.05 AND lock patient coverage (point) >= 0.95; not supported if the 99%
   upper bound < -0.05 or coverage < 0.95; undecided otherwise (as H2).
Conventions as step A2 (deviation log C9, C11): one-sided 99% bounds = 1st / 99th percentiles of 2,000 bootstrap
means (fresh default_rng(20261111) per metric); fully unactionable share and O-share per patient over the kept
outputs (one per seed, all valid), patients with no kept output excluded from H4 (count reported); valid among
requested = kept valid outputs / 5; coverage = at least one kept output. Movability null: exact per patient,
100,000 Monte Carlo draws, seed 20261111 (frozen A2 code). Secondaries: 95% intervals, Clopper-Pearson for
patient proportions. Numbers in the note are truncated to 4 decimals.

Usage (p7-carla312 venv): python -I b_analysis.py [--lof]
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

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import b_common as C  # noqa: E402

D = C.stats()
DELTA, H5_MARGIN, H4_FLOOR = 0.05, -0.05, 0.10
REQ = 5


def q(bs, p):
    return float(np.quantile(bs, p))


def boot(x, levels=(0.95,)):
    x = np.asarray(x, float)
    if len(x) == 0:
        return {"n": 0, "est": float("nan")}, np.array([np.nan])
    bs = D.boot_means(x)
    out = {"n": int(len(x)), "est": float(np.mean(x))}
    for lv in levels:
        a = (1 - lv) / 2
        out[f"ci{int(round(lv * 100))}"] = [q(bs, a), q(bs, 1 - a)]
    return out, bs


def sets(series):
    return [set(s.split(";")) - {""} for s in series.fillna("")]


def readings():
    from depgraph.edges import EDGES
    T = C.roles()
    E_all = {(e.src, e.dst) for e in EDGES}
    E_gr = {(e.src, e.dst) for e in EDGES if e.grade in ("A", "B", "C", "E")}
    def leak(S, E, k, strict):
        return any(not D.supported(v, S, E, k, strict, role=T) for v in S if T.get(v) == "indicator")
    return {"ada_k1": lambda S: leak(S, E_all, 1, False), "ada_graded_k1": lambda S: leak(S, E_gr, 1, False),
            "ada_k2_permissive": lambda S: leak(S, E_all, 2, False), "ada_k2_strict": lambda S: leak(S, E_all, 2, True)}


def describe(outputs: pd.DataFrame, pids, n_req, cols, x_of, span, movd=None):
    """Descriptive block for one generator x mode: outputs has pid, changed, cost (valid outputs only)."""
    T = C.roles()
    R = readings()
    res = {}
    n = len(pids)
    S = sets(outputs["changed"]) if len(outputs) else []
    outputs = outputs.copy()
    outputs["S"] = S
    cnt = outputs.groupby("pid").size().reindex(pids).fillna(0).to_numpy()
    cov = int((cnt > 0).sum())
    res["coverage"] = {"x": cov, "n": n, "share": cov / n, "cp95": D.clopper_pearson(cov, n, 0.95),
                       "cp99": D.clopper_pearson(cov, n, 0.99)}
    res["valid_among_requested"], _ = boot(cnt / n_req)
    if not len(outputs):
        return res, pd.DataFrame(columns=["fully", "best"]), outputs
    outputs["fully"] = [C.audit(sorted(s))["fully_unactionable"] for s in S]
    outputs["touch"] = [any(T.get(f) == "indicator" for f in s) for s in S]
    outputs["n_ind"] = [sum(T.get(f) == "indicator" for f in s) for s in S]
    outputs["n_chg"] = [len(s) for s in S]
    for name, fn in R.items():
        outputs[f"leak_{name}"] = [fn(s) for s in S]
    g = outputs.groupby("pid")
    per = g.agg(fully=("fully", "mean"), touch=("touch", "mean"), ind=("n_ind", "sum"), chg=("n_chg", "sum"),
                cost=("cost", "mean"), best=("cost", "min"), nchg=("n_chg", "mean"),
                **{f"leak_{k}": (f"leak_{k}", "mean") for k in R})
    per["oshare"] = np.where(per["chg"] > 0, per["ind"] / per["chg"].where(per["chg"] > 0, 1), 0.0)
    for k in ["fully", "touch", "oshare", "cost", "best", "nchg"] + [f"leak_{r}" for r in R]:
        res[k], _ = boot(per[k].to_numpy())
    res["n_outputs"] = int(len(outputs))
    res["distinct_outputs_per_patient"], _ = boot(
        g["changed"].agg(lambda s: len(set(s))).to_numpy() if "point_key" not in outputs else g["point_key"].nunique().to_numpy())
    res["share_outputs_fully_unactionable"] = float(outputs["fully"].mean())
    res["share_outputs_leaking_ada_k1"] = float(outputs["leak_ada_k1"].mean())
    res["feature_change_counts"] = dict(Counter(f for s in S for f in s).most_common())
    return res, per, outputs


def movability_null(outputs, movd):
    T = C.roles()
    observed, nulls, outside, sizes = [], [], 0, []
    for pid, g in outputs.groupby("pid"):
        cnt = Counter(f for s in sets(g["changed"]) for f in s)
        Mv = movd[int(pid)]
        outside += sum(v for f, v in cnt.items() if f not in Mv)
        n_ind = sum(T.get(f) == "indicator" for f in Mv)
        observed.append(D.oshare(cnt, [f for f in cnt if T.get(f) == "indicator"]))
        nulls.append(D.patient_null(cnt, Mv, n_ind))
        sizes.append(len(nulls[-1]))
    T_, p, n_ge = D.movability_null_p(observed, nulls, draws=100_000, seed=20261111)
    return {"T_mean_oshare": T_, "null_mean_of_means": float(np.mean([v.mean() for v in nulls])), "p": p,
            "draws": 100_000, "n_draws_ge": n_ge, "n_patients": len(observed), "max_subsets_per_patient": int(max(sizes)),
            "changes_outside_movable_set": int(outside)}


def change_sizes(outputs, x_by_pid, cols):
    """Among route-supported outputs that move an indicator: |change| in GenHlth levels / PhysHlth, MentHlth days,
    per supporting lever (ADA k = 1)."""
    par = C.ada_lever_parents()
    rows = []
    for r in outputs.itertuples():
        S = set(str(r.changed).split(";")) - {""}
        x = x_by_pid[int(r.pid)]
        for v in ("GenHlth", "PhysHlth", "MentHlth"):
            if v in S:
                sup = [u for u in par.get(v, []) if u in S]
                if sup:
                    j = cols.index(v)
                    rows.append({"indicator": v, "size": abs(getattr(r, f"cf_{v}") - x[j]), "levers": "+".join(sup)})
    if not rows:
        return {}
    d = pd.DataFrame(rows)
    return {f"{v}|{l}": {"n": int(len(g)), "mean": float(g["size"].mean()), "median": float(g["size"].median()),
                         "max": float(g["size"].max())} for (v, l), g in d.groupby(["indicator", "levers"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lof", action="store_true")
    a = ap.parse_args()
    C.check_prereg()
    C.below_normal()
    X, y, Xtr, Xte, ytr, yte = C.load_brfss()
    cols = list(X.columns)
    lo, span = C.ranges(cols)
    res = {"written": datetime.now().strftime("%d/%m/%Y %H:%M")}
    lof = None
    if a.lof:
        from sklearn.neighbors import LocalOutlierFactor
        lof = LocalOutlierFactor(n_neighbors=20, novelty=True).fit(C.to_scaled(Xtr.to_numpy(), lo, span))

    def lof_block(outputs):
        if lof is None or not len(outputs):
            return None
        P = C.to_scaled(outputs[[f"cf_{c}" for c in cols]].to_numpy(float), lo, span)
        sc = -lof.score_samples(P)
        per = pd.Series(sc, index=outputs["pid"].to_numpy()).groupby(level=0).mean().to_numpy()
        return boot(per)[0] | {"share_outputs_predicted_outlier": float(np.mean(lof.predict(P) == -1))}

    for model in ("mlp", "lr"):
        W = C.OUT / f"wachter_{model}"
        if not (W / "run_info.json").exists():
            res[f"wachter_{model}"] = {"status": "not run"}
            continue
        info = json.loads((W / "run_info.json").read_text(encoding="utf-8"))
        coh = pd.read_csv(C.OUT / "models" / model / "cohort.csv")
        pids = np.arange(len(coh))
        queries = Xte.iloc[coh["test_pos"].to_numpy()].reset_index(drop=True)
        x_by_pid = {i: queries.iloc[i].to_numpy(float) for i in pids}
        mv = pd.read_csv(W / "movability.csv").fillna({"movable": ""})
        movd = {int(r.pid): [f for f in r.movable.split(";") if f] for r in mv.itertuples()}
        block = {"cohort_n": len(pids), "model_info": json.loads((C.OUT / "models" / model / "model_info.json").read_text()),
                 "run_info": {k: v for k, v in info.items() if k != "patterns"}}
        kept, rows, per = {}, {}, {}
        for mode in ("published", "lock", "route"):
            fk = W / f"kept_{mode}.csv"
            if not fk.exists() or info.get(f"status_{mode}") != "complete":
                block[mode] = {"status": info.get(f"status_{mode}", "not run")}
                continue
            kept[mode] = pd.read_csv(fk).fillna({"changed": ""})
            rows[mode] = pd.read_csv(W / f"rows_{mode}.csv").fillna({"changed": ""})
            kept[mode]["point_key"] = kept[mode][[f"cf_{c}" for c in cols]].astype(str).agg("|".join, axis=1)
            d, per[mode], _ = describe(kept[mode], pids, REQ, cols, x_by_pid, span)
            fr = rows[mode][rows[mode]["feasible"]]
            d["runs"] = {"n_runs": int(len(rows[mode])), "feasible_runs": int(len(fr)),
                         "valid_before_rounding": float(fr["valid_pre"].mean()),
                         "valid_after_rounding": float(fr["valid_post"].mean()),
                         "valid_after_given_before": float(fr.loc[fr["valid_pre"], "valid_post"].mean()) if fr["valid_pre"].any() else float("nan"),
                         "mean_iterations": float(fr["iters"].mean()), "share_capped_runs": float((~fr["valid_pre"]).mean())}
            d["kept_valid_before_rounding"] = float(kept[mode]["valid_pre"].mean()) if len(kept[mode]) else float("nan")
            d["cpu_hours"] = float(info.get(f"cpu_secs_{mode}", np.nan)) / 3600
            d["lof"] = lof_block(kept[mode])
            if mode == "route":
                d["change_sizes_route_supported"] = change_sizes(kept[mode], x_by_pid, cols)
            block[mode] = d
        if "published" in kept:
            block["published_change_sizes_supported"] = change_sizes(
                kept["published"][[C.audit(sorted(s))["route_ok"] for s in sets(kept["published"]["changed"])]],
                x_by_pid, cols)
        # ---------------- primary decisions (MLP) / same statistics reported for LR as secondary
        lv = (0.95, 0.99)
        dec = {}
        if "published" in kept:
            pp = per["published"]
            oa1, bs = boot(pp["fully"].to_numpy(), lv)
            oa1["lower_one_sided_99"], oa1["upper_one_sided_99"] = q(bs, 0.01), q(bs, 0.99)
            oa1["patients_without_output"] = int(len(pids) - len(pp))
            nul = movability_null(kept["published"], movd)
            lo1, hi1, p = oa1["lower_one_sided_99"], oa1["upper_one_sided_99"], nul["p"]
            v = "supported" if (lo1 > H4_FLOOR and p < 0.01) else ("not supported" if (hi1 <= H4_FLOOR or p >= 0.5) else "undecided")
            v2 = ("supported" if (oa1["ci99"][0] > H4_FLOOR and p < 0.01) else
                  "not supported" if (oa1["ci99"][1] <= H4_FLOOR or p >= 0.5) else "undecided")
            dec["H4"] = {"verdict": v, "fully_unactionable": oa1, "movability_null": nul,
                         "component_i_lower99_gt_0.10": lo1 > H4_FLOOR, "component_ii_p_lt_0.01": p < 0.01,
                         "verdict_if_two_sided_99": v2}
        else:
            dec["H4"] = {"verdict": "not reached"}
        if "published" in kept and "lock" in kept:
            cnt = {m: kept[m].groupby("pid").size().reindex(pids).fillna(0).to_numpy() for m in ("published", "lock")}
            dd, bs = boot((cnt["lock"] - cnt["published"]) / REQ, lv)
            dd["lower_one_sided_99"], dd["upper_one_sided_99"] = q(bs, 0.01), q(bs, 0.99)
            dd["published_valid_among_requested"] = float((cnt["published"] / REQ).mean())
            dd["lock_valid_among_requested"] = float((cnt["lock"] / REQ).mean())
            pv = dd["published_valid_among_requested"]
            dd["relative_loss"] = float((pv - dd["lock_valid_among_requested"]) / pv) if pv > 0 else float("nan")
            x = int((cnt["lock"] > 0).sum())
            lcov = x / len(pids)
            v = ("supported" if (dd["lower_one_sided_99"] > H5_MARGIN and lcov >= 0.95) else
                 "not supported" if (dd["upper_one_sided_99"] < H5_MARGIN or lcov < 0.95) else "undecided")
            v2 = ("supported" if (dd["ci99"][0] > H5_MARGIN and lcov >= 0.95) else
                  "not supported" if (dd["ci99"][1] < H5_MARGIN or lcov < 0.95) else "undecided")
            dec["H5"] = {"verdict": v, "delta_valid_among_requested": dd, "lock_coverage_point": lcov,
                         "lock_coverage_cp99": D.clopper_pearson(x, len(pids), 0.99), "lock_coverage_x": x,
                         "verdict_if_two_sided_99": v2}
        else:
            dec["H5"] = {"verdict": "not reached"}
        if "lock" in kept and "route" in kept:
            bl, br = per["lock"]["best"], per["route"]["best"]
            pair = sorted(set(bl.index) & set(br.index))
            dlt = bl.loc[pair].to_numpy() - br.loc[pair].to_numpy()
            eq, _ = boot(dlt, (0.95, 0.98))
            lo98, hi98 = eq.get("ci98", [np.nan, np.nan])
            verdict = ("equivalent" if (lo98 > -DELTA and hi98 < DELTA) else
                       "not equivalent" if (lo98 >= DELTA or hi98 <= -DELTA) else "undecided")
            dec["S_route_vs_lock_best_kept_cost_TOST"] = eq | {"delta": DELTA, "reading": verdict, "n_paired": len(pair),
                                                               "n_route_only": len(set(br.index) - set(bl.index)),
                                                               "n_lock_only": len(set(bl.index) - set(br.index))}
        if model == "lr" and "published" in kept:
            import pickle
            with open(C.OUT / "models" / "lr" / "lr_pipeline.pkl", "rb") as fh:
                pipe = pickle.load(fh)
            sc, lrm = pipe.named_steps["scale"], pipe.named_steps["lr"]
            a_s = lrm.coef_[0] / sc.scale_ * span  # coefficient per scaled unit (class-1 logit)
            FT = C.p7().FT
            agree, inset, nn = 0, 0, 0
            for r in kept["published"].itertuples():
                x = x_by_pid[int(r.pid)]
                Mv = movd[int(r.pid)]
                best_f, best_v = None, -1.0
                for f in Mv:
                    j = cols.index(f)
                    mut = FT._effective_mutability(FT.FEATURE_TAXONOMY[f]).value
                    ok_dir = (mut == "bidirectional") or (mut == "monotonic_up" and a_s[j] < 0) or (mut == "monotonic_down" and a_s[j] > 0)
                    if ok_dir and abs(a_s[j]) > best_v:
                        best_f, best_v = f, abs(a_s[j])
                cf = np.array([getattr(r, f"cf_{c}") for c in cols])
                ds = np.abs(cf - x) / span
                nn += 1
                agree += best_f is not None and cols[int(np.argmax(ds))] == best_f
                inset += best_f is not None and best_f in str(r.changed).split(";")
            dec["S_lr_port_check"] = {"n_outputs": nn, "share_largest_scaled_change_is_predicted_feature": agree / nn,
                                      "share_predicted_feature_in_change_set": inset / nn}
        block["decisions"] = dec
        res[f"wachter_{model}"] = block

    # ----------------------------------------------------------------- Growing Spheres, AR, MINT (secondary)
    for meth, mname, nreq in (("gs", "xgb", 5), ("ar", "lr", 5)):
        Wd = C.OUT / f"{meth}_{mname}"
        if not (Wd / "run_info.json").exists():
            res[meth] = {"status": "not run"}
            continue
        info = json.loads((Wd / "run_info.json").read_text(encoding="utf-8"))
        coh = pd.read_csv(C.OUT / "models" / mname / "cohort.csv")
        pids = np.arange(len(coh))
        queries = Xte.iloc[coh["test_pos"].to_numpy()].reset_index(drop=True)
        x_by_pid = {i: queries.iloc[i].to_numpy(float) for i in pids}
        mv = pd.read_csv(Wd / "movability.csv").fillna({"movable": ""})
        movd = {int(r.pid): [f for f in r.movable.split(";") if f] for r in mv.itertuples()}
        blk = {"run_info": info}
        per = {}
        for mode in ("published", "lock", "route"):
            fk = Wd / f"out_{mode}.csv"
            if not fk.exists():
                blk[mode] = {"status": "not run"}
                continue
            o = pd.read_csv(fk).fillna({"changed": ""})
            if meth == "gs":
                allo = o
                o = o[o["found"] & o["valid_post"]].copy()
            else:
                allo = o
                o = o[o["valid_post"]].copy()
            o["point_key"] = o[[f"cf_{c}" for c in cols]].astype(str).agg("|".join, axis=1)
            d, per[mode], _ = describe(o, pids, nreq, cols, x_by_pid, span)
            if meth == "gs":
                d["valid_before_rounding_of_kept"] = float(o["valid_pre"].mean()) if len(o) else float("nan")
                d["mean_layers"] = float(allo["layers"].mean())
            else:
                d["mip_outputs_invalid_after_check"] = int((~allo["valid_post"]).sum()) if len(allo) else 0
            d["cpu_hours"] = float(info.get(f"cpu_secs_{mode}", np.nan)) / 3600
            d["status"] = info.get(f"status_{mode}")
            d["lof"] = lof_block(o)
            if mode == "published" and len(o):
                d["movability_null"] = movability_null(o, movd)
            if mode == "route":
                d["change_sizes_route_supported"] = change_sizes(o, x_by_pid, cols)
            blk[mode] = d
        if "published" in per and "lock" in per:
            cntp = pd.read_csv(Wd / "out_published.csv")
            cntl = pd.read_csv(Wd / "out_lock.csv")
            def vc(o):
                o = o[o["found"] & o["valid_post"]] if meth == "gs" else o[o["valid_post"]]
                return o.groupby("pid").size().reindex(pids).fillna(0).to_numpy()
            blk["delta_valid_among_requested_lock_minus_published"] = boot((vc(cntl) - vc(cntp)) / nreq)[0]
        if "lock" in per and "route" in per:
            bl, br = per["lock"]["best"], per["route"]["best"]
            pair = sorted(set(bl.index) & set(br.index))
            blk["best_cost_lock_minus_route"] = boot(bl.loc[pair].to_numpy() - br.loc[pair].to_numpy(), (0.95, 0.98))[0]
        res[meth] = blk
    Wd = C.OUT / "mint_xgb"
    if (Wd / "out_published.csv").exists():
        o = pd.read_csv(Wd / "out_published.csv").fillna({"changed": "", "interventions": "", "propagated": ""})
        o = o[o["found"]]
        R = readings()
        S = sets(o["changed"])
        T = C.roles()
        res["mint"] = {"run_info": json.loads((Wd / "run_info.json").read_text(encoding="utf-8")),
                       "n_outputs": int(len(o)), "t_max_treatable_on_path": 1,
                       "leaks_k1": int(sum(R["ada_k1"](s) for s in S)),
                       "leaks_k2_permissive": int(sum(R["ada_k2_permissive"](s) for s in S)),
                       "leaks_k2_strict": int(sum(R["ada_k2_strict"](s) for s in S)),
                       "outputs_with_propagated_changes": int((o["propagated"] != "").sum()),
                       "outputs_moving_an_indicator": int(sum(any(T.get(f) == "indicator" for f in s) for s in S)),
                       "propagated_feature_counts": dict(Counter(f for s in sets(o["propagated"]) for f in s)),
                       "proposition2_k_ge_1_plus_t_no_leak": int(sum(R["ada_k2_strict"](s) for s in S)) == 0}
    else:
        res["mint"] = {"status": "not run"}
    C.write_json(C.OUT / "analysis" / "b_results.json", res)
    print(json.dumps({k: (v.get("decisions") if isinstance(v, dict) and "decisions" in v else None) for k, v in res.items()},
                     default=float, indent=1)[:4000])


if __name__ == "__main__":
    main()
