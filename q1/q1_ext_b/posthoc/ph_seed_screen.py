"""POST-HOC B-P1, step 1: seed screen of the preregistered MLP (plan section 2).

The frozen `b_models.train_mlp` (CARLA ANN 18-9-3, ReLU, Adam lr 0.002, batch 1,024, 20 epochs, BCE on softmax vs
one-hot, scaled inputs) is run with seeds 43, 44, ... in order; only the seed changes (torch.manual_seed and the
DataLoader shuffle generator). Live unit = ReLU output > 0 for at least one training row (trained network = the
acceptance criterion; at initialisation for information). Eligible = test p >= 0.5. Accepted when every hidden layer
has >= 1 live unit and >= 50 eligible. Stop at 5 accepted or 30 tried.

Harness check first (not a post-hoc model): seed 42 through this harness must give the B-E2 evidence (alive 18, 8, 0
at init and after training; constant p 0.1421...) and the saved seed-42 state dict and constant p; otherwise stop.

Usage (p7-carla312 venv): python -I ph_seed_screen.py
Outputs: q1_ext_b_posthoc/models/mlp_s<seed>/ (state dict, test_proba.csv, cohort.csv, model_info.json) and
q1_ext_b_posthoc/seed_screen.json / .csv.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ph_common as PH  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

import b_common as C  # noqa: E402
import b_models as BM  # noqa: E402


def alive_units(m, S: np.ndarray):
    """Per hidden layer: number of units whose ReLU output is > 0 on at least one row of S."""
    x = torch.from_numpy(np.asarray(S, np.float32))
    alive = None
    with torch.no_grad():
        for b in range(0, len(x), 65536):
            h = x[b:b + 65536]
            cur = []
            for i, layer in enumerate(m.layers[:-1]):
                h = m.relu(layer(h))
                cur.append((h > 0).any(dim=0))
            alive = cur if alive is None else [a | c for a, c in zip(alive, cur)]
    return [int(a.sum()) for a in alive]


def init_alive(seed: int, d: int, Str):
    import b_vendor as V
    torch.manual_seed(seed)
    m = V.carla_ann()(d, BM.MLP["hidden"], 2)
    return alive_units(m, Str)


def fit(seed: int, Str, ytr):
    saved = dict(BM.MLP)
    BM.MLP["seed"] = seed  # the only change (plan section 2); restored below
    try:
        m, hist = BM.train_mlp(Str, ytr)
    finally:
        BM.MLP.clear()
        BM.MLP.update(saved)
    return m, hist


def main():
    PH.check()
    C.below_normal()
    t0 = time.time()
    from sklearn.metrics import roc_auc_score
    X, y, Xtr, Xte, ytr, yte = C.load_brfss()
    cols = list(X.columns)
    lo, span = C.ranges(cols)
    Str, Ste = C.to_scaled(Xtr.to_numpy(), lo, span), C.to_scaled(Xte.to_numpy(), lo, span)
    PH.OUT.mkdir(parents=True, exist_ok=True)
    log = open(PH.OUT / "seed_screen_log.txt", "a", encoding="utf-8")

    def say(msg):
        line = f"{datetime.now():%d/%m/%Y %H:%M:%S} {msg}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    # ---- harness check on seed 42 (B-E2 evidence)
    m42, _ = fit(42, Str, ytr.to_numpy())
    p42 = BM.mlp_proba1(m42, Ste)
    # the frozen run saved only the seed-42 state dict and degenerate_check.json (no test probabilities)
    ref_sd = torch.load(C.OUT / "models" / "mlp" / "mlp_state_dict.pt")
    ref_p = json.loads((C.OUT / "models" / "mlp" / "degenerate_check.json").read_text(encoding="utf-8"))["seed42_trained"]
    sd = m42.state_dict()
    hc = {"alive_init": init_alive(42, len(cols), Str), "alive_trained": alive_units(m42, Str),
          "p_min": float(p42.min()), "p_max": float(p42.max()),
          "max_abs_diff_vs_saved_seed42_state_dict": float(max((sd[k] - ref_sd[k]).abs().max() for k in ref_sd)),
          "saved_p": [ref_p["test_p1_min"], ref_p["test_p1_max"]]}
    hc["ok"] = bool(hc["alive_init"] == [18, 8, 0] and hc["alive_trained"] == [18, 8, 0]
                    and hc["max_abs_diff_vs_saved_seed42_state_dict"] == 0.0
                    and hc["p_min"] == ref_p["test_p1_min"] and hc["p_max"] == ref_p["test_p1_max"])
    say(f"harness check seed 42: {hc}")
    if not hc["ok"]:
        C.write_json(PH.OUT / "seed_screen.json", {"label": PH.LABEL, "harness_check_seed42": hc, "status": "stopped"})
        sys.exit("harness check failed: seed 42 does not reproduce B-E2")

    table, accepted = [], []
    seed = PH.FIRST_SEED
    while len(table) < PH.MAX_TRIED and len(accepted) < PH.MAX_ACCEPTED:
        ts = time.time()
        a_init = init_alive(seed, len(cols), Str)
        m, hist = fit(seed, Str, ytr.to_numpy())
        a_tr = alive_units(m, Str)
        proba = BM.mlp_proba1(m, Ste)
        auc = float(roc_auc_score(yte, proba))
        n_el = int((proba >= 0.5).sum())
        ok_alive = all(a >= 1 for a in a_tr)
        ok_el = n_el >= PH.MIN_ELIGIBLE
        acc = bool(ok_alive and ok_el)
        reason = "" if acc else "; ".join(r for r, bad in (("a hidden layer has no live unit", not ok_alive),
                                                             (f"fewer than {PH.MIN_ELIGIBLE} eligible", not ok_el)) if bad)
        row = {"order": len(table) + 1, "seed": seed, "alive_init": a_init, "alive_trained": a_tr, "test_auc": auc,
               "eligible_p_ge_0_5": n_el, "test_p_min": float(proba.min()), "test_p_max": float(proba.max()),
               "final_train_loss": hist[-1], "accepted": acc, "reject_reason": reason, "secs": time.time() - ts}
        table.append(row)
        d = PH.mlp_dir(seed)
        d.mkdir(parents=True, exist_ok=True)
        torch.save(m.state_dict(), d / "mlp_state_dict.pt")
        idx = C.cohort(proba)
        pd.DataFrame({"test_pos": np.arange(len(Xte)), "test_index": Xte.index, "proba1": proba}).to_csv(
            d / "test_proba.csv", index=False)
        pd.DataFrame({"pid": np.arange(len(idx)), "test_pos": idx, "test_index": Xte.index[idx],
                      "proba1": proba[idx]}).to_csv(d / "cohort.csv", index=False)
        C.write_json(d / "model_info.json", {"label": PH.LABEL, "model": "mlp", "config": dict(BM.MLP, seed=seed),
                                             "train_loss_per_epoch": hist, **{k: v for k, v in row.items()},
                                             "cohort_n": int(len(idx)),
                                             "cohort_min_p": float(proba[idx].min()) if len(idx) else None})
        if acc:
            accepted.append(seed)
        say(f"seed {seed}: alive init {a_init} trained {a_tr}; AUC {C.trunc(auc)}; eligible {n_el}; "
            f"{'ACCEPTED' if acc else 'rejected: ' + reason}")
        seed += 1
    stop = "5 accepted" if len(accepted) >= PH.MAX_ACCEPTED else "30 tried"
    res = {"label": PH.LABEL, "plan_sha256": PH.PLAN_SHA256, "harness_check_seed42": hc, "seeds_tried": table,
           "accepted": accepted, "n_tried": len(table), "stop_reason": stop, "secs": time.time() - t0,
           "written": datetime.now().strftime("%d/%m/%Y %H:%M")}
    C.write_json(PH.OUT / "seed_screen.json", res)
    pd.DataFrame(table).to_csv(PH.OUT / "seed_screen.csv", index=False)
    say(f"stop ({stop}): accepted {accepted} of {len(table)} tried")


if __name__ == "__main__":
    main()
