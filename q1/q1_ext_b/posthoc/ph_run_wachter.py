"""POST-HOC B-P1, step 2: Wachter on one accepted MLP seed (plan section 3).

Identical to the frozen `b_run_wachter.py` run loop (equal search effort, P = 24 per generator seed, generator seeds
42, 123, 2024, 7, 31337, modes published | lock | route, CARLA core without t_max_min and with the B-D1 cap, the
batched-vs-single precheck, the 4 CPU-hour budget per mode), with only the model and output paths changed: the MLP
of seed <s> from the seed screen and its own cohort (P7 rule). The frozen helpers make_problem and precheck and the
frozen b_methods are imported unchanged. The seed must be one accepted by the screen.

Usage (p7-carla312 venv): python -I ph_run_wachter.py --seed S [--modes published,lock,route] [--chunk 8]
Outputs: q1_ext_b_posthoc/wachter_mlp_s<S>/ rows_<mode>.csv, kept_<mode>.csv, movability.csv, run_info.json, log.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ph_common as PH  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import psutil  # noqa: E402
import torch  # noqa: E402

import b_common as C  # noqa: E402
import b_methods as M  # noqa: E402
import b_run_wachter as RW  # noqa: E402


def load_mlp(seed, cols, lo, span):
    """As b_run_wachter.load_model('mlp'), from the post-hoc model folder of this seed."""
    import b_vendor as V
    m = V.carla_ann()(len(cols), [18, 9, 3], 2)
    m.load_state_dict(torch.load(PH.mlp_dir(seed) / "mlp_state_dict.pt"))
    m.eval()

    def proba0(R):
        with torch.no_grad():
            return m(torch.from_numpy(C.to_scaled(np.atleast_2d(R), lo, span).astype(np.float32))).numpy()[:, 0].astype(float)

    def predict0(R):
        with torch.no_grad():
            out = m(torch.from_numpy(C.to_scaled(np.atleast_2d(R), lo, span).astype(np.float32))).numpy()
        return np.argmax(out, axis=1) == 0
    return m, predict0, proba0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--modes", default="published,lock,route")
    ap.add_argument("--chunk", type=int, default=8)
    a = ap.parse_args()
    PH.check()
    C.below_normal()
    torch.set_num_threads(1)
    scr = json.loads((PH.OUT / "seed_screen.json").read_text(encoding="utf-8"))
    if a.seed not in scr["accepted"]:
        sys.exit(f"seed {a.seed} was not accepted by the screen")
    import b_vendor as V
    V.verify()
    X, y, Xtr, Xte, ytr, yte = C.load_brfss()
    cols = list(X.columns)
    lo, span = C.ranges(cols)
    tm, predict0, proba0 = load_mlp(a.seed, cols, lo, span)
    coh = pd.read_csv(PH.mlp_dir(a.seed) / "cohort.csv")
    # the reloaded model must give the saved test probabilities of the cohort
    pr = 1 - proba0(Xte.iloc[coh["test_pos"].to_numpy()].to_numpy(float))
    if np.abs(pr - coh["proba1"].to_numpy()).max() > 1e-6:
        sys.exit("reloaded MLP does not reproduce the saved cohort probabilities")
    queries = Xte.iloc[coh["test_pos"].to_numpy()].reset_index(drop=True)
    outd = PH.wachter_dir(a.seed)
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
    problems = [RW.make_problem(queries.iloc[i], cols, lo, span, predict0, proba0) for i in range(len(queries))]
    mv = pd.DataFrame({"pid": range(len(problems)),
                       "movable": [";".join(C.movable(pb.grids["published"], pd.Series(pb.x, index=cols))) for pb in problems]})
    mv.to_csv(outd / "movability.csv", index=False)
    info_p = outd / "run_info.json"
    info = json.loads(info_p.read_text(encoding="utf-8")) if info_p.exists() else {}
    if "precheck_max_abs_diff" not in info:
        md = RW.precheck(tm, problems[0])
        info["precheck_max_abs_diff"] = md
        say(f"precheck batched vs single core, patient 0: max abs diff {md:.3g}")
        if md > 1e-4:
            C.write_json(info_p, info)
            sys.exit("precheck failed: batched core differs from single-run core")
    info.update(label=PH.LABEL, model="mlp", mlp_seed=a.seed, cohort_n=len(problems), P=P, wachter=M.WACHTER,
                seeds=C.SEEDS, patterns=[{k: v for k, v in p.items()} for p in pats], torch=torch.__version__)
    proc = psutil.Process()
    for mode in a.modes.split(","):
        if info.get(f"status_{mode}") == "complete":
            say(f"mlp s{a.seed} {mode}: already complete")
            continue
        fr, fk = outd / f"rows_{mode}.csv", outd / f"kept_{mode}.csv"
        done = set(pd.read_csv(fr)["pid"]) if fr.exists() else set()
        cpu_key = f"cpu_secs_{mode}"
        cpu_prev = float(info.get(cpu_key, 0.0))
        c0 = sum(proc.cpu_times()[:2])
        todo = [i for i in range(len(problems)) if i not in done]
        say(f"mlp s{a.seed} {mode}: {len(todo)} patients to run ({len(done)} done)")
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
            say(f"mlp s{a.seed} {mode}: patients {ids[0]}-{ids[-1]} done in {time.time() - t0:.0f} s; kept "
                f"{len(dk)}/{5 * len(ids)}; cpu {used / 3600:.2f} h")
            if used > RW.BUDGET_CPU_SECS:
                status = "not reached (CPU budget)"
                break
        info[f"status_{mode}"] = status
        C.write_json(info_p, info)
        say(f"mlp s{a.seed} {mode}: {status}")


if __name__ == "__main__":
    main()
