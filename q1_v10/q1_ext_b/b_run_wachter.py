"""Extension B runs: Wachter on the MLP (primary, H4/H5) or on LR (secondary), BRFSS 2021 diabetes (prereg v3 5.3-5.5).

Equal search effort: in every mode (published | lock | route), for each of the five seeds, P = 24 runs; the valid
rounded result of lowest scaled L1 cost is kept (b_methods). Wachter settings: vendored CARLA defaults (lr 0.01,
lambda 0.01, n_iter 1000 per lambda step, L1, BCE) with the wall-clock rule removed and a cap of 10 lambda steps
(deviation log B-D1). Budget (5.4): 4 CPU-hours of process CPU time per model x mode; exceeding it stops that mode
as "not reached". Before the runs the batched core is checked against the single-run core on one real patient
(4 rows, <= 1e-4 per coordinate); a mismatch stops the script.

Usage (p7-carla312 venv): python -I b_run_wachter.py --model mlp|lr [--modes published,lock,route] [--chunk 8]
Outputs: outputs/q1_ext_b/wachter_<model>/ rows_<mode>.csv (every run), kept_<mode>.csv (kept outputs with the
rounded point), movability.csv, run_info.json, log.
"""
from __future__ import annotations

import argparse
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
import torch  # noqa: E402

import b_common as C  # noqa: E402
import b_methods as M  # noqa: E402
import b_wachter_core as W  # noqa: E402

BUDGET_CPU_SECS = 4 * 3600


class LRTorch(torch.nn.Module):
    """The fitted sklearn LR pipeline as a function of the scaled features: z = coef . ((lo + s span - mu) / sd) + b."""

    def __init__(self, pipe, lo, span):
        super().__init__()
        sc, lr = pipe.named_steps["scale"], pipe.named_steps["lr"]
        self.a = torch.tensor((lr.coef_[0] / sc.scale_ * span).astype(np.float32))
        self.c = float(lr.intercept_[0] + np.sum(lr.coef_[0] * (lo - sc.mean_) / sc.scale_))

    def forward(self, s):
        z = s @ self.a + self.c
        return torch.softmax(torch.stack([torch.zeros_like(z), z], dim=-1), dim=-1)


def load_model(name, cols, lo, span):
    mdir = C.OUT / "models" / name
    if name == "mlp":
        import b_vendor as V
        m = V.carla_ann()(len(cols), [18, 9, 3], 2)
        m.load_state_dict(torch.load(mdir / "mlp_state_dict.pt"))
        m.eval()

        def proba0(R):
            with torch.no_grad():
                return m(torch.from_numpy(C.to_scaled(np.atleast_2d(R), lo, span).astype(np.float32))).numpy()[:, 0].astype(float)

        def predict0(R):
            with torch.no_grad():
                out = m(torch.from_numpy(C.to_scaled(np.atleast_2d(R), lo, span).astype(np.float32))).numpy()
            return np.argmax(out, axis=1) == 0
        return m, predict0, proba0, None
    with open(mdir / "lr_pipeline.pkl", "rb") as fh:
        pipe = pickle.load(fh)
    tm = LRTorch(pipe, lo, span)
    predict0 = lambda R: pipe.predict(pd.DataFrame(np.atleast_2d(R), columns=cols)) == 0  # noqa: E731
    proba0 = lambda R: pipe.predict_proba(pd.DataFrame(np.atleast_2d(R), columns=cols))[:, 0]  # noqa: E731
    return tm, predict0, proba0, pipe


def make_problem(q, cols, lo, span, predict0, proba0):
    P = C.p7()
    grids = {}
    for mode in ("published", "lock"):
        with C.Taxonomy(mode):
            grids[mode] = C.p4_grids(q, cols)
    return M.Problem(x=q.to_numpy(float), cols=cols, lo=lo, span=span, grids=grids, predict0=predict0, proba0=proba0,
                     route_ok=lambda ch: bool(P.admissible(list(ch))), lever_parents=C.ada_lever_parents(),
                     patterns=C.route_patterns())


def precheck(tm, pb):
    """Batched core vs single-run core on one real patient, 4 published rows (seed 42)."""
    rows = M.rows_for_patient(pb, "published", 4, seeds=[42])
    LO, HI, FX = zip(*[M.box(pb, r["grids"]) for r in rows])
    p = M.WACHTER
    res, *_ = W.wachter_batch(tm, pb.s, np.array([r["start"] for r in rows]), np.array(LO), np.array(HI), p["lr"],
                              p["lambda_param"], p["y_target"], p["n_iter"], p["norm"], p["max_lambda_steps"],
                              fixed=np.array(FX))
    md = 0.0
    for k, r in enumerate(rows):
        lo_t, hi_t = torch.tensor(LO[k], dtype=torch.float32), torch.tensor(HI[k], dtype=torch.float32)
        fx, xt = torch.tensor(FX[k]), torch.tensor(pb.s[None], dtype=torch.float32)

        def proj(z, lo_t=lo_t, hi_t=hi_t, fx=fx, xt=xt):
            return torch.where(fx, xt, torch.minimum(torch.maximum(z, lo_t), hi_t))

        single = W.wachter_recourse_edited(tm, pb.s[None], [], True, None, p["lr"], p["lambda_param"], p["y_target"],
                                           p["n_iter"], p["norm"], True, "BCE", max_lambda_steps=p["max_lambda_steps"],
                                           x_init=r["start"][None], project=proj)
        md = max(md, float(np.abs(single - res[k]).max()))
    return md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["mlp", "lr"], required=True)
    ap.add_argument("--modes", default="published,lock,route")
    ap.add_argument("--chunk", type=int, default=8)
    a = ap.parse_args()
    C.check_prereg()
    C.below_normal()
    torch.set_num_threads(1)
    import b_vendor as V
    V.verify()
    X, y, Xtr, Xte, ytr, yte = C.load_brfss()
    cols = list(X.columns)
    lo, span = C.ranges(cols)
    tm, predict0, proba0, pipe = load_model(a.model, cols, lo, span)
    coh = pd.read_csv(C.OUT / "models" / a.model / "cohort.csv")
    queries = Xte.iloc[coh["test_pos"].to_numpy()].reset_index(drop=True)
    outd = C.OUT / f"wachter_{a.model}"
    outd.mkdir(parents=True, exist_ok=True)
    log = open(outd / "log.txt", "a", encoding="utf-8")

    def say(msg):
        line = f"{datetime.now():%d/%m/%Y %H:%M:%S} {msg}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    pats = C.route_patterns()
    P = len(pats)
    assert P == 24, P
    problems = [make_problem(queries.iloc[i], cols, lo, span, predict0, proba0) for i in range(len(queries))]
    mv = pd.DataFrame({"pid": range(len(problems)),
                       "movable": [";".join(C.movable(pb.grids["published"], pd.Series(pb.x, index=cols))) for pb in problems]})
    mv.to_csv(outd / "movability.csv", index=False)
    info_p = outd / "run_info.json"
    info = json.loads(info_p.read_text(encoding="utf-8")) if info_p.exists() else {}
    if "precheck_max_abs_diff" not in info:
        md = precheck(tm, problems[0])
        info["precheck_max_abs_diff"] = md
        say(f"precheck batched vs single core, patient 0: max abs diff {md:.3g}")
        if md > 1e-4:
            C.write_json(info_p, info)
            sys.exit("precheck failed: batched core differs from single-run core")
    info.update(model=a.model, cohort_n=len(problems), P=P, wachter=M.WACHTER, seeds=C.SEEDS,
                patterns=[{k: v for k, v in p.items()} for p in pats], torch=torch.__version__)
    proc = psutil.Process()
    for mode in a.modes.split(","):
        fr, fk = outd / f"rows_{mode}.csv", outd / f"kept_{mode}.csv"
        done = set(pd.read_csv(fr)["pid"]) if fr.exists() else set()
        cpu_key = f"cpu_secs_{mode}"
        cpu_prev = float(info.get(cpu_key, 0.0))
        c0 = sum(proc.cpu_times()[:2])
        todo = [i for i in range(len(problems)) if i not in done]
        say(f"{a.model} {mode}: {len(todo)} patients to run ({len(done)} done)")
        status = "complete"
        for k in range(0, len(todo), a.chunk):
            ids = todo[k:k + a.chunk]
            t0 = time.time()
            rowsets = [M.rows_for_patient(problems[i], mode, P) for i in ids]
            results = M.wachter_rows(tm, [problems[i] for i in ids], rowsets)
            recs_all, kept_all = [], []
            for i, rows, res in zip(ids, rowsets, results):
                recs = M.finish_rows(problems[i], rows, res, mode)
                for r in recs:
                    pt = r.pop("point")
                    r["pid"] = i
                    recs_all.append(r)
                    if r.get("kept"):
                        kept_all.append({"pid": i, "seed": r["seed"], "j": r["j"], "cost": r["cost"],
                                         "changed": r["changed"], "valid_pre": r["valid_pre"],
                                         **{f"cf_{c}": float(v) for c, v in zip(cols, pt)}})
            dr = pd.DataFrame(recs_all)[["pid", "seed", "j", "feasible", "valid_pre", "valid_post", "route_ok",
                                         "kept", "cost", "changed", "iters", "lsteps"]]
            dr.to_csv(fr, mode="a", header=not fr.exists(), index=False)
            dk = pd.DataFrame(kept_all, columns=["pid", "seed", "j", "cost", "changed", "valid_pre"] + [f"cf_{c}" for c in cols])
            dk.to_csv(fk, mode="a", header=not fk.exists(), index=False)
            used = cpu_prev + sum(proc.cpu_times()[:2]) - c0
            info[cpu_key] = used
            C.write_json(info_p, info)
            say(f"{a.model} {mode}: patients {ids[0]}-{ids[-1]} done in {time.time() - t0:.0f} s; kept "
                f"{len(dk)}/{5 * len(ids)}; cpu {used / 3600:.2f} h")
            if used > BUDGET_CPU_SECS:
                status = "not reached (CPU budget)"
                break
        info[f"status_{mode}"] = status
        C.write_json(info_p, info)
        say(f"{a.model} {mode}: {status}")


if __name__ == "__main__":
    main()
