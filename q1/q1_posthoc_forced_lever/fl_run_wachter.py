"""POST HOC (S-P4), exploratory: lock plus forced lever, a graph-free baseline for route-aware enforcement.

Plan: prereg/posthoc_forced_lever_plan_en_v1_20261112_0957.md (hash checked below). The frozen extension B and
B-P1 modules (b_common, b_methods, b_wachter_core, b_run_wachter, posthoc/ph_common, posthoc/ph_run_wachter) are
imported unchanged. Only the grids of each run differ from the frozen run loop:

  forced    (FL-G, primary)   lock grids (GenHlth, PhysHlth, MentHlth fixed) + run j forces nothing (j = 1) or the
                              feature F[(j - 2) mod 9], F = every lever and treatable in role-table order. No edge,
                              no route information.
  lockroute (FL-R, secondary) lock grids + run j forces exactly the levers route-aware pattern j forces; no
                              indicator is ever freed.

Forcing rule (B-C1 d, for any feature): values at least one grid step from x_u in the P4 permitted direction; for a
bidirectional feature the side whose nearest forced value gives the higher class-0 probability (tie: down). A run
whose forced feature cannot move is infeasible (no output, counted in the 24). Everything else as the frozen loop:
P = 24 runs per generator seed, seeds 42, 123, 2024, 7, 31337, starts from default_rng(seed * 1000 + j), rounding
psi, kept output = valid rounded result of lowest scaled L1 cost per seed, 4 CPU-hour budget per mode.

Usage (p7-carla312 venv): python -I fl_run_wachter.py --model mlp --seed 46 [--modes forced,lockroute]
                          python -I fl_run_wachter.py --model lr [--modes forced,lockroute]
Outputs: outputs/q1_posthoc_forced_lever/wachter_mlp_s<S>/ or wachter_lr/: rows_<mode>.csv, kept_<mode>.csv,
run_info.json, log.txt.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS / "q1_ext_b"))
sys.path.insert(0, str(TOOLS / "q1_ext_b" / "posthoc"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import psutil  # noqa: E402
import torch  # noqa: E402

import b_common as C  # noqa: E402
import b_methods as M  # noqa: E402
import b_run_wachter as RW  # noqa: E402
import ph_common as PH  # noqa: E402

PLAN = C.PAPER7 / "prereg" / "posthoc_forced_lever_plan_en_v1_20261112_0957.md"
PLAN_SHA256 = "b1c7624aea42fa4e7911e869db77e71f44ccbe9dc983416acaf53c214cdf87e0"
OUT = C.PAPER7 / "outputs" / "q1_posthoc_forced_lever"
LABEL = "POST HOC (S-P4), exploratory; frozen verdicts unchanged (H4/H5 NOT REACHED, B-E2)"


def check():
    C.check_prereg()
    if C.sha256_file(PLAN) != PLAN_SHA256:
        sys.exit("S-P4 plan hash mismatch")
    if "OMP_NUM_THREADS" in os.environ:
        sys.exit("OMP_NUM_THREADS is set; unset it (bug B-E3)")


def action_features():
    """F: every lever and treatable of the role table (depgraph TIER), in role-table order."""
    T = C.roles()
    return [f for f, r in T.items() if r in ("lever", "treatable")]


def forced_sets(mode):
    if mode == "forced":
        F = action_features()
        return [()] + [(F[(j - 2) % len(F)],) for j in range(2, 25)]
    if mode == "lockroute":
        return [tuple(sorted({u for u in p.values() if u is not None})) for p in C.route_patterns()]
    raise ValueError(mode)


def forced_grids(pb, forced):
    """Lock grids with the forced features restricted; None when a forced feature cannot move (infeasible)."""
    FT = C.p7().FT
    G = {f: g.copy() for f, g in pb.grids["lock"].items()}
    q = pd.Series(pb.x, index=pb.cols)
    for u in forced:
        g = pb.grids["lock"][u]
        if not np.any(np.abs(g - float(q[u])) > 1e-9):
            return None
        mut = FT._effective_mutability(FT.FEATURE_TAXONOMY[u]).value
        if mut in ("monotonic_up", "monotonic_down"):
            fg = C.forced_grid(u, q, g)
            if not len(fg):
                return None
            G[u] = fg
            continue
        cand = []
        for side in (-1, +1):
            fg = C.forced_grid(u, q, g, side)
            if len(fg):
                near = fg[np.argmin(np.abs(fg - float(q[u])))]
                z = pb.x.copy()
                z[pb.cols.index(u)] = near
                cand.append((-float(pb.proba0(z[None])[0]), side, fg))
        if not cand:
            return None
        cand.sort(key=lambda t: (t[0], t[1]))
        G[u] = cand[0][2]
    return G


def rows_for_patient(pb, sets, seeds=C.SEEDS):
    rows = []
    d = len(pb.cols)
    for seed in seeds:
        for j in range(1, len(sets) + 1):
            G = forced_grids(pb, sets[j - 1])
            start = pb.s + np.random.default_rng(seed * 1000 + j).normal(0.0, M.WACHTER["start_sd"], d)
            rows.append({"seed": seed, "j": j, "grids": G, "start": start, "forced": ";".join(sets[j - 1])})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["mlp", "lr"], required=True)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--modes", default="forced,lockroute")
    ap.add_argument("--chunk", type=int, default=8)
    a = ap.parse_args()
    check()
    C.below_normal()
    torch.set_num_threads(1)
    import b_vendor as V
    V.verify()
    X, y, Xtr, Xte, ytr, yte = C.load_brfss()
    cols = list(X.columns)
    lo, span = C.ranges(cols)
    if a.model == "mlp":
        import ph_run_wachter as PR
        scr = json.loads((PH.OUT / "seed_screen.json").read_text(encoding="utf-8"))
        if a.seed not in scr["accepted"]:
            sys.exit(f"seed {a.seed} was not accepted by the B-P1 screen")
        tm, predict0, proba0 = PR.load_mlp(a.seed, cols, lo, span)
        coh = pd.read_csv(PH.mlp_dir(a.seed) / "cohort.csv")
        pr = 1 - proba0(Xte.iloc[coh["test_pos"].to_numpy()].to_numpy(float))
        if np.abs(pr - coh["proba1"].to_numpy()).max() > 1e-6:
            sys.exit("reloaded MLP does not reproduce the saved cohort probabilities")
        ref_dir = PH.wachter_dir(a.seed)
        outd = OUT / f"wachter_mlp_s{a.seed}"
        tag = f"mlp s{a.seed}"
    else:
        tm, predict0, proba0, _ = RW.load_model("lr", cols, lo, span)
        coh = pd.read_csv(C.OUT / "models" / "lr" / "cohort.csv")
        ref_dir = C.OUT / "wachter_lr"
        outd = OUT / "wachter_lr"
        tag = "lr"
    queries = Xte.iloc[coh["test_pos"].to_numpy()].reset_index(drop=True)
    outd.mkdir(parents=True, exist_ok=True)
    log = open(outd / "log.txt", "a", encoding="utf-8")

    def say(msg):
        line = f"{datetime.now():%d/%m/%Y %H:%M:%S} {msg}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    problems = [RW.make_problem(queries.iloc[i], cols, lo, span, predict0, proba0) for i in range(len(queries))]
    info_p = outd / "run_info.json"
    info = json.loads(info_p.read_text(encoding="utf-8")) if info_p.exists() else {}
    if "precheck_max_abs_diff" not in info:
        md = RW.precheck(tm, problems[0])
        info["precheck_max_abs_diff"] = md
        say(f"precheck batched vs single core, patient 0: max abs diff {md:.3g}")
        if md > 1e-4:
            C.write_json(info_p, info)
            sys.exit("precheck failed")
    info.update(label=LABEL, plan_sha256=PLAN_SHA256, model=a.model, mlp_seed=a.seed, cohort_n=len(problems),
                P=24, wachter=M.WACHTER, seeds=C.SEEDS, action_features=action_features(),
                forced_sets={m: [";".join(s) for s in forced_sets(m)] for m in ("forced", "lockroute")},
                torch=torch.__version__)
    proc = psutil.Process()
    for mode in a.modes.split(","):
        sets = forced_sets(mode)
        assert len(sets) == 24
        if info.get(f"status_{mode}") == "complete":
            say(f"{tag} {mode}: already complete")
            continue
        fr, fk = outd / f"rows_{mode}.csv", outd / f"kept_{mode}.csv"
        done = set(pd.read_csv(fr)["pid"]) if fr.exists() else set()
        cpu_key = f"cpu_secs_{mode}"
        cpu_prev = float(info.get(cpu_key, 0.0))
        c0 = sum(proc.cpu_times()[:2])
        todo = [i for i in range(len(problems)) if i not in done]
        say(f"{tag} {mode}: {len(todo)} patients to run ({len(done)} done)")
        status = "complete"
        for k in range(0, len(todo), a.chunk):
            ids = todo[k:k + a.chunk]
            t0 = time.time()
            rowsets = [rows_for_patient(problems[i], sets) for i in ids]
            results = M.wachter_rows(tm, [problems[i] for i in ids], rowsets)
            recs_all, kept_all = [], []
            for i, rows, res in zip(ids, rowsets, results):
                recs = M.finish_rows(problems[i], rows, res, mode)
                for r, row in zip(recs, rows):
                    pt = r.pop("point")
                    r["pid"] = i
                    r["forced"] = row["forced"]
                    recs_all.append(r)
                    if r.get("kept"):
                        kept_all.append({"pid": i, "seed": r["seed"], "j": r["j"], "cost": r["cost"],
                                         "changed": r["changed"], "valid_pre": r["valid_pre"], "forced": row["forced"],
                                         **{f"cf_{c}": float(v) for c, v in zip(cols, pt)}})
            dr = pd.DataFrame(recs_all)[["pid", "seed", "j", "forced", "feasible", "valid_pre", "valid_post",
                                         "route_ok", "kept", "cost", "changed", "iters", "lsteps"]]
            dr.to_csv(fr, mode="a", header=not fr.exists(), index=False)
            dk = pd.DataFrame(kept_all, columns=["pid", "seed", "j", "cost", "changed", "valid_pre", "forced"]
                              + [f"cf_{c}" for c in cols])
            dk.to_csv(fk, mode="a", header=not fk.exists(), index=False)
            used = cpu_prev + sum(proc.cpu_times()[:2]) - c0
            info[cpu_key] = used
            C.write_json(info_p, info)
            say(f"{tag} {mode}: patients {ids[0]}-{ids[-1]} done in {time.time() - t0:.0f} s; kept "
                f"{len(dk)}/{5 * len(ids)}; cpu {used / 3600:.2f} h")
            if used > RW.BUDGET_CPU_SECS:
                status = "not reached (CPU budget)"
                break
        info[f"status_{mode}"] = status
        # run j = 1 of 'forced' equals lock run j = 1 (same grids, same start): share of identical results
        if mode == "forced" and status == "complete":
            mine = pd.read_csv(fr)
            ref = pd.read_csv(ref_dir / "rows_lock.csv")
            m1 = mine[mine.j == 1].merge(ref[ref.j == 1], on=["pid", "seed", "j"], suffixes=("", "_lock"))
            same = (m1.valid_post == m1.valid_post_lock) & (m1.changed.fillna("") == m1.changed_lock.fillna(""))
            info["j1_equals_lock_share"] = float(same.mean()) if len(m1) else None
            info["j1_pairs"] = int(len(m1))
        C.write_json(info_p, info)
        say(f"{tag} {mode}: {status}")


if __name__ == "__main__":
    main()
