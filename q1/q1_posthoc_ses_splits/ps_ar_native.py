"""POST HOC (S-P3), exploratory: Actionable Recourse on the frozen BRFSS 2021 logistic regression with the
percentile-shift cost of Ustun et al. (2019) instead of the preregistered range-scaled L1 cost.

Everything else is the frozen extension B setting (b_common, b_run_wachter.make_problem, b_methods.ar_flipset):
same fitted LR pipeline, same cohort (models/lr/cohort.csv), same P4 action grid per patient and mode, same
flipset of 5 by no-good cuts on the change set, same lock and route constraints, same validity check.
Only the objective changes:
  Q_j(v)      = share of TRAINING rows with x_j <= v (empirical CDF of feature j);
  c_j(a)      = |Q_j(a) - Q_j(x_j)|  (percentile shift of the action x_j -> a);
  objective   = max_j c_j(a_j)  (maximum percentile shift, MPS)  + 1e-3 * sum_j c_j(a_j)  (tie-break).
Outputs: outputs/q1_posthoc_ses_splits/ar_lr_mps/out_{mode}.csv and analysis JSON (frozen b_analysis.describe and
movability_null, with the frozen L1-cost run analysed by the same code for the side-by-side comparison).

Usage (p7-carla312 venv): python -I ps_ar_native.py
"""
from __future__ import annotations

import json
import pickle
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS / "q1_ext_b"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import b_common as C  # noqa: E402
import b_methods as M  # noqa: E402
import b_analysis as BA  # noqa: E402
from b_run_wachter import make_problem  # noqa: E402

OUT = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/q1_posthoc_ses_splits/ar_lr_mps")
SES = ["Education", "Income", "AnyHealthcare"]


def ar_flipset_mps(pb, mode, w_raw, b_raw, Q, size=5, eps=1e-6, indicators=C.INDICATORS_LOCK):
    import mip
    G = pb.grids["lock" if mode == "lock" else "published"]
    cols, x = pb.cols, pb.x
    z0 = float(w_raw @ x + b_raw)
    m = mip.Model(sense=mip.MINIMIZE, solver_name="CBC")
    m.verbose = 0
    m.threads = 1
    acts, zf, costs = {}, {}, []
    for i, f in enumerate(cols):
        vals = [float(a) for a in G[f] if abs(a - x[i]) > 1e-9]
        acts[f] = [(a, m.add_var(var_type=mip.BINARY)) for a in vals]
        if acts[f]:
            m += mip.xsum(u for _, u in acts[f]) <= 1
            zf[f] = mip.xsum(u for _, u in acts[f])
    m += z0 + mip.xsum(w_raw[i] * (a - x[i]) * u for i, f in enumerate(cols) for a, u in acts[f]) <= -eps
    if mode == "route":
        for v in indicators:
            if v in zf:
                par = [zf[u] for u in pb.lever_parents.get(v, []) if u in zf]
                m += zf[v] <= (mip.xsum(par) if par else 0)
    t = m.add_var(lb=0.0)
    for i, f in enumerate(cols):
        for a, u in acts[f]:
            c = abs(Q[f](a) - Q[f](x[i]))
            costs.append(c * u)
            m += t >= c * u
    m.objective = t + 1e-3 * mip.xsum(costs)
    out = []
    for _ in range(size):
        st = m.optimize()
        if st != mip.OptimizationStatus.OPTIMAL:
            break
        xc = x.copy()
        S = []
        for i, f in enumerate(cols):
            for a, u in acts[f]:
                if u.x is not None and u.x > 0.5:
                    xc[i] = a
                    S.append(f)
        mps = max([abs(Q[f](xc[i]) - Q[f](x[i])) for i, f in enumerate(cols)] or [0.0])
        out.append({"point": xc, "changed": C.change_set(x, xc, cols), "cost": C.l1_scaled(x, xc, pb.span),
                    "mps": mps, "score": float(w_raw @ xc + b_raw)})
        if not S:
            break
        m += mip.xsum(zf[f] for f in S) - mip.xsum(zf[f] for f in zf if f not in S) <= len(S) - 1
    return out


def ses_block(o):
    S = BA.sets(o["changed"]) if len(o) else []
    T = C.roles()
    n = len(S)
    if not n:
        return {"n_outputs": 0}
    touch = [bool(s & set(SES)) for s in S]
    only = [bool(s) and s <= set(SES) for s in S]
    noact = [bool(s) and not any(T.get(f) in ("lever", "treatable") for f in s) for s in S]
    return {"n_outputs": n, "ses_touch": float(np.mean(touch)), "ses_only": float(np.mean(only)),
            "no_lever_or_treatable": float(np.mean(noact))}


def main():
    C.check_prereg()
    C.below_normal()
    X, y, Xtr, Xte, ytr, yte = C.load_brfss()
    cols = list(X.columns)
    lo, span = C.ranges(cols)
    mdir = C.OUT / "models" / "lr"
    with open(mdir / "lr_pipeline.pkl", "rb") as fh:
        pipe = pickle.load(fh)
    f = lambda R: pd.DataFrame(np.atleast_2d(R), columns=cols)  # noqa: E731
    predict0 = lambda R: pipe.predict(f(R)) == 0  # noqa: E731
    proba0 = lambda R: pipe.predict_proba(f(R))[:, 0]  # noqa: E731
    sc, lr = pipe.named_steps["scale"], pipe.named_steps["lr"]
    w_raw = lr.coef_[0] / sc.scale_
    b_raw = float(lr.intercept_[0] - np.sum(lr.coef_[0] * sc.mean_ / sc.scale_))
    coh = pd.read_csv(mdir / "cohort.csv")
    queries = Xte.iloc[coh["test_pos"].to_numpy()].reset_index(drop=True)
    problems = [make_problem(queries.iloc[i], cols, lo, span, predict0, proba0) for i in range(len(queries))]
    tr = {c: np.sort(Xtr[c].to_numpy(float)) for c in cols}
    Q = {c: (lambda v, a=tr[c]: float(np.searchsorted(a, v + 1e-9, side="right")) / len(a)) for c in cols}
    OUT.mkdir(parents=True, exist_ok=True)
    info = {"cohort_n": len(problems), "cost": "maximum percentile shift + 1e-3 total percentile shift",
            "percentile": "empirical CDF on the training split (seed 42)"}
    for mode in ("published", "lock", "route"):
        t0 = time.time()
        recs = []
        for i, pb in enumerate(problems):
            for k, r in enumerate(ar_flipset_mps(pb, mode, w_raw, b_raw, Q, size=5)):
                recs.append({"pid": i, "rank": k, "valid_post": bool(predict0(r["point"][None])[0]),
                             "score": r["score"], "cost": r["cost"], "mps": r["mps"], "changed": ";".join(r["changed"]),
                             **{f"cf_{c}": float(v) for c, v in zip(cols, r["point"])}})
        pd.DataFrame(recs).to_csv(OUT / f"out_{mode}.csv", index=False)
        info[f"secs_{mode}"] = time.time() - t0
        print(f"{mode}: {len(recs)} outputs, {time.time() - t0:.0f} s", flush=True)

    # ------------------------------------------------------------------ analysis, both costs, same code
    pids = np.arange(len(problems))
    x_by_pid = {i: queries.iloc[i].to_numpy(float) for i in pids}
    mv = pd.read_csv(C.OUT / "ar_lr" / "movability.csv").fillna({"movable": ""})
    movd = {int(r.pid): [f for f in r.movable.split(";") if f] for r in mv.itertuples()}
    res = {"info": info}
    for label, d in (("l1_frozen", C.OUT / "ar_lr"), ("mps_posthoc", OUT)):
        blk = {}
        cnt = {}
        for mode in ("published", "lock", "route"):
            o = pd.read_csv(d / f"out_{mode}.csv").fillna({"changed": ""})
            o = o[o["valid_post"]].copy()
            o["point_key"] = o[[f"cf_{c}" for c in cols]].astype(str).agg("|".join, axis=1)
            desc, per, _ = BA.describe(o, pids, 5, cols, x_by_pid, span)
            keep = {k: desc[k] for k in ("coverage", "valid_among_requested", "fully", "touch", "leak_ada_k1",
                                         "oshare", "nchg") if k in desc}
            keep["share_outputs_fully_unactionable"] = desc.get("share_outputs_fully_unactionable")
            keep["feature_change_counts"] = desc.get("feature_change_counts")
            keep["ses"] = ses_block(o)
            if mode == "published" and len(o):
                keep["movability_null"] = BA.movability_null(o, movd)
            blk[mode] = keep
            cnt[mode] = o.groupby("pid").size().reindex(pids).fillna(0).to_numpy() / 5
        dv, _ = BA.boot(cnt["lock"] - cnt["published"])
        blk["delta_valid_lock_minus_published"] = dv
        res[label] = blk
    C.write_json(OUT / "ar_native_results.json", res)
    for label in ("l1_frozen", "mps_posthoc"):
        p = res[label]["published"]
        print(label, "fully", p["fully"]["est"], "touch", p["touch"]["est"], "unsupported", p["leak_ada_k1"]["est"],
              "mov p", p.get("movability_null", {}).get("p"))


if __name__ == "__main__":
    main()
