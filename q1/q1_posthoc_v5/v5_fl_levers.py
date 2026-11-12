"""POST HOC (S-P5), exploratory: levers-only forced-lever baseline (FL-L) for projected Wachter.

Plan: prereg/posthoc_v5_plan_en_v1_20261112_1211.md, Section 4 (hash checked below). Identical to FL-G of S-P4
(tools/q1_posthoc_forced_lever/fl_run_wachter.py, imported unchanged: forced_grids, rows_for_patient, the frozen
loop and kept rule), except the candidate set: F_L = the genuine behaviours of the role table, in role-table order
(BMI, PhysActivity, Fruits, Veggies, Smoker, HvyAlcoholConsump). Run j = 1 forces nothing; run j >= 2 forces
F_L[(j - 2) mod 6]. HighBP, HighChol (ever-told diagnosis flags) and NoDocbcCost (access barrier) are never forced
and keep their published grids, as in the runs they are compared with.

Usage (p7-carla312 venv): python -I v5_fl_levers.py --model mlp --seed 46
                          python -I v5_fl_levers.py --model lr
Outputs: outputs/q1_posthoc_v5/wachter_mlp_s<S>/ or wachter_lr/: rows_levers.csv, kept_levers.csv, run_info.json,
log.txt.
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
sys.path.insert(0, str(TOOLS / "q1_posthoc_forced_lever"))
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
import fl_run_wachter as FL  # noqa: E402  (S-P4 code, unchanged; its check() verifies the S-P4 plan hash)

PLAN = C.PAPER7 / "prereg" / "posthoc_v5_plan_en_v1_20261112_1211.md"
PLAN_SHA256 = open(HERE / "PLAN_SHA256.txt", encoding="utf-8").read().split()[0]
OUT = C.PAPER7 / "outputs" / "q1_posthoc_v5"
LABEL = "POST HOC (S-P5), exploratory; frozen verdicts unchanged (H4/H5 NOT REACHED, B-E2)"
LEVERS_R5 = ["BMI", "PhysActivity", "Fruits", "Veggies", "Smoker", "HvyAlcoholConsump"]
MODE = "levers"


def check():
    FL.check()
    if C.sha256_file(PLAN) != PLAN_SHA256:
        sys.exit("S-P5 plan hash mismatch")


def lever_set():
    T = C.roles()
    F = [f for f, r in T.items() if r == "lever" and f in LEVERS_R5]
    assert F == LEVERS_R5, F
    return F


def forced_sets():
    F = lever_set()
    return [()] + [(F[(j - 2) % len(F)],) for j in range(2, 25)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["mlp", "lr"], required=True)
    ap.add_argument("--seed", type=int, default=None)
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
    sets = forced_sets()
    assert len(sets) == 24
    info.update(label=LABEL, plan_sha256=PLAN_SHA256, model=a.model, mlp_seed=a.seed, cohort_n=len(problems), P=24,
                wachter=M.WACHTER, seeds=C.SEEDS, levers_r5=lever_set(), forced_sets={MODE: [";".join(s) for s in sets]},
                torch=torch.__version__)
    if info.get(f"status_{MODE}") == "complete":
        say(f"{tag} {MODE}: already complete")
        return
    proc = psutil.Process()
    fr, fk = outd / f"rows_{MODE}.csv", outd / f"kept_{MODE}.csv"
    done = set(pd.read_csv(fr)["pid"]) if fr.exists() else set()
    cpu_key = f"cpu_secs_{MODE}"
    cpu_prev = float(info.get(cpu_key, 0.0))
    c0 = sum(proc.cpu_times()[:2])
    todo = [i for i in range(len(problems)) if i not in done]
    say(f"{tag} {MODE}: {len(todo)} patients to run ({len(done)} done)")
    status = "complete"
    for k in range(0, len(todo), a.chunk):
        ids = todo[k:k + a.chunk]
        t0 = time.time()
        rowsets = [FL.rows_for_patient(problems[i], sets) for i in ids]
        results = M.wachter_rows(tm, [problems[i] for i in ids], rowsets)
        recs_all, kept_all = [], []
        for i, rows, res in zip(ids, rowsets, results):
            recs = M.finish_rows(problems[i], rows, res, "forced")
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
        say(f"{tag} {MODE}: patients {ids[0]}-{ids[-1]} done in {time.time() - t0:.0f} s; kept "
            f"{len(dk)}/{5 * len(ids)}; cpu {used / 3600:.2f} h")
        if used > RW.BUDGET_CPU_SECS:
            status = "not reached (CPU budget)"
            break
    info[f"status_{MODE}"] = status
    if status == "complete":
        mine = pd.read_csv(fr)
        ref = pd.read_csv(ref_dir / "rows_lock.csv")
        m1 = mine[mine.j == 1].merge(ref[ref.j == 1], on=["pid", "seed", "j"], suffixes=("", "_lock"))
        same = (m1.valid_post == m1.valid_post_lock) & (m1.changed.fillna("") == m1.changed_lock.fillna(""))
        info["j1_equals_lock_share"] = float(same.mean()) if len(m1) else None
        info["j1_pairs"] = int(len(m1))
    C.write_json(info_p, info)
    say(f"{tag} {MODE}: {status}")


if __name__ == "__main__":
    main()
