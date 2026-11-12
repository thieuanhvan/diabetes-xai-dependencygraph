"""POST HOC (S-P5), exploratory: results of the levers-only forced-lever baseline (plan Sections 4-5). Reads files only.

Modes per network: published, lock, route-aware (frozen B-P1 / extension B files), FL-G 'forced' and FL-R
'lockroute' (S-P4 files), FL-L 'levers' (S-P5 files). Networks: MLP seeds 44, 45, 46, 48, 49 and LR.
Primary: Delta_L = coverage(route-aware) - coverage(FL-L), pooled over MLP seeds 46, 48, 49, 95% cluster bootstrap
over test patients (2,000, default_rng(20261111)), margin 0.10, read as S-P4 Section 7. Secondary: Delta_R (restated),
Delta_G beside Delta_L, per seed, all five networks, LR; action coverage (patients with a kept output that changes a
genuine lever, R5) and the share of kept outputs changing HighBP or HighChol.
Shares over kept outputs are given under the v4 reading (lever or treatable = action) and under R5.
Usage (p7-carla312 venv): python -I v5_fl_analysis.py
Output: outputs/q1_posthoc_v5/analysis/forced_lever_levers_only.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "q1_posthoc_forced_lever"))
sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
import fl_analysis as FA  # noqa: E402  (S-P4 analysis helpers, unchanged)

PAPER7 = Path("D:/20-study/uit/research/diabetesxai/paper7")
PLAN = PAPER7 / "prereg" / "posthoc_v5_plan_en_v1_20261112_1211.md"
PLAN_SHA256 = open(HERE / "PLAN_SHA256.txt", encoding="utf-8").read().split()[0]
O = PAPER7 / "outputs"
V5 = O / "q1_posthoc_v5"
L5 = {"BMI", "PhysActivity", "Fruits", "Veggies", "Smoker", "HvyAlcoholConsump"}
DX = {"HighBP", "HighChol"}
MODES = ["published", "lock", "route", "forced", "lockroute", "levers"]


def dirs(tag):
    old, s4, coh = FA.wachter_dirs(tag)
    new = V5 / ("wachter_lr" if tag == "lr" else f"wachter_mlp_s{int(tag[1:])}")
    return old, s4, new, coh


def r5_shares(changed, inds):
    S = [set(s.split(";")) - {""} for s in changed.fillna("")]
    n = len(S)
    if not n:
        return {"n": 0}
    return {"n": n, "no_action_r5": sum(bool(s) and not (s & L5) for s in S) / n,
            "fully_unactionable_r5": sum(bool(s & inds) and not (s & L5) for s in S) / n,
            "changes_highbp_or_highchol": sum(bool(s & DX) for s in S) / n,
            "changes_highbp_or_highchol_without_lever": sum(bool(s & DX) and not (s & L5) for s in S) / n}


def block(tag, roles):
    old, s4, new, cfile = dirs(tag)
    coh = pd.read_csv(cfile)
    n = len(coh)
    inds = {f for f, r in roles.items() if r == "indicator"}
    out, cov, acov = {"cohort_n": n}, {}, {}
    for mode in MODES:
        base = old if mode in ("published", "lock", "route") else (s4 if mode in ("forced", "lockroute") else new)
        fr, fk = base / f"rows_{mode}.csv", base / f"kept_{mode}.csv"
        info = json.loads((base / "run_info.json").read_text(encoding="utf-8")) if (base / "run_info.json").exists() else {}
        if not fr.exists() or info.get(f"status_{mode}") != "complete":
            out[mode] = {"status": info.get(f"status_{mode}", "not run")}
            continue
        rows = pd.read_csv(fr).fillna({"changed": ""})
        try:
            kept = pd.read_csv(fk).fillna({"changed": ""})
        except pd.errors.EmptyDataError:
            kept = pd.DataFrame(columns=["pid", "changed", "cost"])
        f = rows[rows["feasible"]]
        x = int(kept["pid"].nunique())
        cov[mode] = (pd.Series(0, index=range(n)).add(kept.groupby("pid").size(), fill_value=0) > 0)
        S = [set(s.split(";")) - {""} for s in kept["changed"]]
        withlev = kept.assign(lev=pd.Series([bool(s & L5) for s in S], index=kept.index, dtype=bool))
        acov[mode] = (pd.Series(0, index=range(n)).add(withlev.loc[withlev["lev"].to_numpy(dtype=bool)].groupby("pid").size(), fill_value=0) > 0)
        out[mode] = {"coverage_x": x, "coverage": x / n, "coverage_cp95": FA.cp(x, n),
                     "action_coverage_r5_x": int(acov[mode].sum()), "kept_outputs": int(len(kept)),
                     "feasible_runs": int(len(f)),
                     "valid_before_rounding": float(f["valid_pre"].mean()) if len(f) else None,
                     "valid_after_rounding": float(f["valid_post"].mean()) if len(f) else None,
                     "kept_v4": FA.output_shares(kept["changed"], roles), "kept_r5": r5_shares(kept["changed"], inds),
                     "j1_equals_lock_share": info.get("j1_equals_lock_share") if mode in ("forced", "levers") else None,
                     "cpu_hours": float(info.get(f"cpu_secs_{mode}", float("nan"))) / 3600}
        if mode == "forced":
            fk_ = kept.assign(dxf=kept["forced"].fillna("").isin(["HighBP", "HighChol"]))
            out[mode]["kept_with_highbp_or_highchol_forced"] = int(fk_["dxf"].sum())
    return out, cov, acov, coh


def main():
    if hashlib.sha256(PLAN.read_bytes()).hexdigest() != PLAN_SHA256:
        sys.exit("S-P5 plan hash mismatch")
    from depgraph.nodes import TIER
    roles = dict(TIER)
    res = {"label": "POST HOC (S-P5), exploratory; preregistered verdicts unchanged", "plan_sha256": PLAN_SHA256,
           "written": datetime.now().strftime("%d/%m/%Y %H:%M"), "margin": FA.MARGIN, "levers_r5": sorted(L5)}
    W, C, A, H = {}, {}, {}, {}
    for tag in [f"s{s}" for s in FA.MLP_SEEDS] + ["lr"]:
        W[tag], C[tag], A[tag], H[tag] = block(tag, roles)
        c = C[tag]
        n = W[tag]["cohort_n"]
        for a_, b_ in (("route", "levers"), ("route", "forced"), ("route", "lockroute")):
            if a_ in c and b_ in c:
                W[tag][f"delta_{a_}_minus_{b_}"] = (int(c[a_].sum()) - int(c[b_].sum())) / n
    res["wachter"] = W
    pooled = {}
    for name, seeds in (("key_seeds_46_48_49", FA.KEY_SEEDS), ("all_accepted_seeds", FA.MLP_SEEDS)):
        parts = []
        for s in seeds:
            c, a = C[f"s{s}"], A[f"s{s}"]
            if not all(m in c for m in MODES):
                continue
            parts.append(pd.DataFrame({"cluster": H[f"s{s}"]["test_pos"].to_numpy(),
                                       **{m: c[m].to_numpy() for m in MODES},
                                       **{f"a_{m}": a[m].to_numpy() for m in MODES}}))
        if not parts:
            pooled[name] = {"status": "not reached"}
            continue
        df = pd.concat(parts, ignore_index=True)
        dl = FA.cluster_boot_diff(df, "route", "levers")
        dg = FA.cluster_boot_diff(df, "route", "forced")
        dr = FA.cluster_boot_diff(df, "route", "lockroute")
        da = FA.cluster_boot_diff(df, "a_route", "a_levers")
        pooled[name] = {"n_seeds": len(parts), "units": int(len(df)),
                        "coverage": {m: float(df[m].mean()) for m in MODES},
                        "action_coverage_r5": {m: float(df[f"a_{m}"].mean()) for m in MODES},
                        "delta_L_route_minus_levers": dl | {"reading": FA.reading(dl["ci95"])},
                        "delta_G_route_minus_forced_S_P4": dg | {"reading": FA.reading(dg["ci95"])},
                        "delta_R_route_minus_lockroute_S_P4": dr | {"reading": FA.reading(dr["ci95"])},
                        "delta_action_coverage_route_minus_levers": da | {"reading": FA.reading(da["ci95"])}}
    res["pooled"] = pooled
    out = V5 / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    (out / "forced_lever_levers_only.json").write_text(json.dumps(res, indent=2, default=float) + "\n", encoding="utf-8")
    print(json.dumps(pooled, indent=1, default=float))


if __name__ == "__main__":
    main()
