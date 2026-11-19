"""Extension B secondary runs on BRFSS 2021 diabetes (prereg v3 5.1, 5.3): Growing Spheres on XGBoost, Actionable
Recourse on LR, MINT on XGBoost (illustration of Proposition 2 only). Ports in b_methods.py.

  --method gs    modes published | lock | route; five seeds (np.random.seed(seed) per patient); one output each.
  --method ar    modes published | lock | route; flipset of size 5 (deterministic, no seed).
  --method mint  published constraints on the levers; one output per patient; no lock row.
Budgets (5.4): 4 CPU-hours per method x mode; 2 x 10^7 model evaluations for MINT's brute force per patient set.
Usage (p7-carla312 venv): python -I b_run_others.py --method gs|ar|mint [--modes ...]
"""
from __future__ import annotations

import argparse
import itertools
import json
import pickle
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import psutil  # noqa: E402

import b_common as C  # noqa: E402
import b_methods as M  # noqa: E402
from b_run_wachter import make_problem  # noqa: E402

BUDGET_CPU_SECS = 4 * 3600
MINT_EVAL_BUDGET = 2 * 10**7


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["gs", "ar", "mint"], required=True)
    ap.add_argument("--modes", default="published,lock,route")
    a = ap.parse_args()
    C.check_prereg()
    C.below_normal()
    import b_vendor as V
    V.verify()
    X, y, Xtr, Xte, ytr, yte = C.load_brfss()
    cols = list(X.columns)
    lo, span = C.ranges(cols)
    mname = "lr" if a.method == "ar" else "xgb"
    mdir = C.OUT / "models" / mname
    if mname == "xgb":
        info_m = json.loads((mdir / "model_info.json").read_text(encoding="utf-8"))
        if not info_m.get("identity_check", {}).get("identical"):
            sys.exit("XGBoost identity check did not pass; see model_info.json")
        import xgboost as xgb
        model = xgb.XGBClassifier()
        model.load_model(str(mdir / "xgb_model.json"))
        f = lambda R: pd.DataFrame(np.atleast_2d(R), columns=cols)  # noqa: E731
        predict0 = lambda R: model.predict(f(R)) == 0  # noqa: E731
        proba0 = lambda R: model.predict_proba(f(R))[:, 0]  # noqa: E731
    else:
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
    outd = C.OUT / f"{a.method}_{mname}"
    outd.mkdir(parents=True, exist_ok=True)
    log = open(outd / "log.txt", "a", encoding="utf-8")

    def say(msg):
        line = f"{datetime.now():%d/%m/%Y %H:%M:%S} {msg}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    mv = pd.DataFrame({"pid": range(len(problems)),
                       "movable": [";".join(C.movable(pb.grids["published"], pd.Series(pb.x, index=cols))) for pb in problems]})
    mv.to_csv(outd / "movability.csv", index=False)
    info_p = outd / "run_info.json"
    info = json.loads(info_p.read_text(encoding="utf-8")) if info_p.exists() else {}
    info.update(method=a.method, model=mname, cohort_n=len(problems))
    proc = psutil.Process()
    modes = ["published"] if a.method == "mint" else a.modes.split(",")
    for mode in modes:
        fk = outd / f"out_{mode}.csv"
        if fk.exists():
            say(f"{mode}: exists, skipped")
            continue
        c0 = sum(proc.cpu_times()[:2])
        t0 = time.time()
        recs, status = [], "complete"
        gs_mod = V.carla_gs() if a.method == "gs" else None
        if a.method == "mint":
            from depgraph.edges import EDGES
            scm = M.LinearSCM.fit(Xtr, [(e.src, e.dst) for e in EDGES])
            T = C.roles()
            levers = [c for c in cols if T.get(c) == "lever"]
            n_eval = 0
        for i, pb in enumerate(problems):
            if a.method == "gs":
                for seed in C.SEEDS:
                    r = M.gs_search(pb, mode, seed, gs_mod)
                    ch = C.change_set(pb.x, r["point"], cols) if r["found"] else []
                    recs.append({"pid": i, "seed": seed, "found": r["found"], "valid_pre": r["valid_pre"],
                                 "valid_post": r["valid_post"], "layers": r["layers"], "l2": r["l2"],
                                 "cost": C.l1_scaled(pb.x, r["point"], span) if r["found"] else np.nan,
                                 "changed": ";".join(ch),
                                 **{f"cf_{c}": (float(v) if r["found"] else np.nan)
                                    for c, v in zip(cols, r["point"] if r["found"] else [0] * len(cols))}})
            elif a.method == "ar":
                fs = M.ar_flipset(pb, mode, w_raw, b_raw, size=5)
                for k, r in enumerate(fs):
                    recs.append({"pid": i, "rank": k, "valid_post": bool(predict0(r["point"][None])[0]),
                                 "score": r["score"], "cost": r["cost"], "changed": ";".join(r["changed"]),
                                 **{f"cf_{c}": float(v) for c, v in zip(cols, r["point"])}})
            else:
                G = pb.grids["published"]
                xd = dict(zip(cols, pb.x))
                mov = [u for u in levers if len(G[u]) > 1]

                def rounder(c, v, xd=xd):
                    j = cols.index(c)
                    lo_c, hi_c = min(lo[j], xd[c]), max(lo[j] + span[j], xd[c])
                    return float(min(max(np.round(v), np.ceil(lo_c)), np.floor(hi_c)))

                cands = []
                for k in (1, 2, 3):
                    for S in itertools.combinations(mov, k):
                        vals = [[v for v in G[u] if abs(v - xd[u]) > 1e-9] for u in S]
                        for combo in itertools.product(*vals):
                            do = dict(zip(S, combo))
                            new = scm.counterfactual(xd, do, rounder)
                            cands.append((sum(abs(do[u] - xd[u]) / span[cols.index(u)] for u in S), k, S, do, new))
                pts = np.array([[c[4][f] for f in cols] for c in cands]) if cands else np.zeros((0, len(cols)))
                n_eval += len(pts)
                ok = predict0(pts) if len(pts) else np.zeros(0, bool)
                best = None
                for c, v in zip(cands, ok):
                    if v and (best is None or (c[0], c[1]) < (best[0], best[1])):
                        best = c
                if best is None:
                    recs.append({"pid": i, "found": False})
                else:
                    cost, k, S, do, new = best
                    xc = np.array([new[f] for f in cols])
                    ch = C.change_set(pb.x, xc, cols)
                    recs.append({"pid": i, "found": True, "interventions": ";".join(sorted(S)),
                                 "propagated": ";".join(sorted(set(ch) - set(S))), "changed": ";".join(ch),
                                 "action_cost": cost, "cost": C.l1_scaled(pb.x, xc, span),
                                 **{f"cf_{c}": float(v) for c, v in zip(cols, xc)}})
                if n_eval > MINT_EVAL_BUDGET:
                    status = "not reached (evaluation budget)"
                    break
            used = sum(proc.cpu_times()[:2]) - c0
            if used > BUDGET_CPU_SECS:
                status = "not reached (CPU budget)"
                break
            if i % 20 == 19:
                say(f"{a.method} {mode}: {i + 1} patients, {time.time() - t0:.0f} s")
        pd.DataFrame(recs).to_csv(fk, index=False)
        info[f"cpu_secs_{mode}"] = sum(proc.cpu_times()[:2]) - c0
        info[f"status_{mode}"] = status
        if a.method == "mint":
            info["mint_model_evaluations"] = n_eval
            info["mint_scm_order"] = scm.order
        C.write_json(info_p, info)
        say(f"{a.method} {mode}: {status}, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
