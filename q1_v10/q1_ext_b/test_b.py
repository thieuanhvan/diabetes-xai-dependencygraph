"""Unit tests of extension B (prereg v3 5.6). All must pass before any real-data run.

Run (p7-carla312 venv): python -I test_b.py [--only name,name]   (plain asserts; one line per test; JSON summary
in outputs/q1_ext_b/unit_tests/test_b_results.json; exit 1 on any failure). Synthetic data only: no BRFSS row is
read (the P4 taxonomy and the ADA graph are used for the BRFSS feature layout).

Settings that the plan leaves open (clarification B-C3):
- Parity (5.2 route 2): CARLA's own Wachter test configuration (BCE, y_target [0, 1], defaults lr 0.01,
  lambda 0.01, n_iter 1000, norm 1) on a CARLA ANN [18, 9, 3] trained on synthetic data generated here;
  unedited CARLA function with t_max_min = 1e9 against the edited single-run core and the batched core.
- L2 and L1 tests: synthetic logistic model; starting lambda above the value at which the factual is a
  stationary point (L2: ||w||; L1: max_j |w_j| / c_j) and passing 1e-4 above the value at which the stationary
  point reaches the boundary, so that the vendored schedule tracks the stationary points; L2: lr 1e-3, 5,000
  iterations per lambda step (with 1,000 the iterate lags the stationary point and drifts up to 2.6e-3 off the
  w-line); L1: lr 2e-4, 1,000 iterations; 20 points each.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import threading
import time
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

import b_common as C  # noqa: E402
import b_methods as M  # noqa: E402
import b_vendor as V  # noqa: E402
import b_wachter_core as W  # noqa: E402

torch.set_num_threads(1)
RESULTS = {}
FAILED = []


def check(name, cond, **info):
    print(("PASS " if cond else "FAIL ") + name + (" " + json.dumps(info, default=float) if info else ""), flush=True)
    RESULTS[name] = {"pass": bool(cond), **info}
    if not cond:
        FAILED.append(name)


class LinearTorch(torch.nn.Module):
    """p(class 1) = sigmoid(w . (lo + s * span) + b), output [p0, p1] (softmax of [0, z])."""

    def __init__(self, w, b, lo=None, span=None):
        super().__init__()
        d = len(w)
        self.w = torch.tensor(np.asarray(w, np.float32))
        self.b = float(b)
        self.lo = torch.tensor(np.zeros(d, np.float32) if lo is None else np.asarray(lo, np.float32))
        self.span = torch.tensor(np.ones(d, np.float32) if span is None else np.asarray(span, np.float32))

    def forward(self, s):
        z = (self.lo + s * self.span) @ self.w + self.b
        return torch.softmax(torch.stack([torch.zeros_like(z), z], dim=-1), dim=-1)


def synthetic_ann(seed=42, d=6, n=6000):
    """CARLA ANN on synthetic data. A [18, 9, 3] ReLU net can collapse to a constant output (dead units); the
    first seed from `seed` upwards whose output is not constant is used (a constant model has no counterfactual
    and makes the unedited CARLA loop run forever)."""
    for sd in range(seed, seed + 20):
        m, X = _synthetic_ann(sd, d, n)
        with torch.no_grad():
            p1 = m(torch.from_numpy(X)).numpy()[:, 1]
        if p1.std() > 0.1:
            return m, X
    raise RuntimeError("no non-degenerate synthetic ANN")


def _synthetic_ann(seed, d, n):
    Ann = V.carla_ann()
    rng = np.random.default_rng(seed)
    X = rng.random((n, d)).astype(np.float32)
    w = np.array([2.0, -1.0, 1.5, 0.3, 0.0, 1.0])[:d]
    y = (X @ w + rng.normal(0, 0.2, n) > np.median(X @ w)).astype(np.int64)
    torch.manual_seed(seed)
    m = Ann(d, [18, 9, 3], 2)
    opt = torch.optim.Adam(m.parameters(), 0.01)
    Xt, Y = torch.from_numpy(X), torch.nn.functional.one_hot(torch.from_numpy(y), 2).float()
    for _ in range(60):
        perm = torch.randperm(n)
        for i in range(0, n, 256):
            b = perm[i:i + 256]
            opt.zero_grad()
            torch.nn.BCELoss()(m(Xt[b]), Y[b]).backward()
            opt.step()
    return m, X


# ----------------------------------------------------------------------------------------------- tests
def test_vendor():
    try:
        V.verify()
        ok = True
    except SystemExit:
        ok = False
    check("vendor: CARLA files unchanged (SHA-256, commit 24db00a)", ok, commit=V.COMMIT)


def test_parity():
    wr = V.carla_wachter()
    m, X = synthetic_ann()
    with torch.no_grad():
        p1 = m(torch.from_numpy(X)).numpy()[:, 1]
    idx = np.where((p1 < 0.2) & (p1 > 0.01))[0][:10]
    d1 = d2 = 0.0
    for i in idx:
        x = X[i:i + 1].astype(float)
        a = wr(m, x, [], True, None, 0.01, 0.01, [0, 1], 1000, 1e9, 1, True, "BCE")
        b = W.wachter_recourse_edited(m, x, [], True, None, 0.01, 0.01, [0, 1], 1000, 1, True, "BCE")
        c, *_ = W.wachter_batch(m, X[i], np.repeat(X[i:i + 1], 3, 0), np.full((3, 6), -1e9), np.full((3, 6), 1e9),
                                0.01, 0.01, [0, 1], 1000, 1, 10**6)
        d1 = max(d1, float(np.abs(a - b).max()))
        d2 = max(d2, float(np.abs(c - a[None]).max()))
    check("Wachter parity: edited single-run core = unedited CARLA (t_max_min non-binding), <= 1e-4",
          len(idx) == 10 and d1 <= 1e-4, n_points=len(idx), max_abs_diff=d1)
    check("Wachter parity: batched core (3 rows) = unedited CARLA, <= 1e-4", len(idx) == 10 and d2 <= 1e-4,
          max_abs_diff=d2)
    # several factuals in one batch
    Xs = X[idx]
    c, *_ = W.wachter_batch(m, Xs, Xs.copy(), np.full(Xs.shape, -1e9), np.full(Xs.shape, 1e9), 0.01, 0.01, [0, 1],
                            1000, 1, 10**6)
    ref = np.array([wr(m, X[i:i + 1].astype(float), [], True, None, 0.01, 0.01, [0, 1], 1000, 1e9, 1, True, "BCE")
                    for i in idx])
    d3 = float(np.abs(c - ref).max())
    check("Wachter parity: batched core with one factual per row = unedited CARLA, <= 1e-4", d3 <= 1e-4,
          max_abs_diff=d3)


def lam_schedule_start(lam_star, lam_still):
    """Starting lambda above lam_still (the factual is a stationary point) such that the vendored schedule
    (lambda -= 0.05 per step) passes 1e-4 above lam_star, the value at which the stationary point reaches the
    boundary; the next step then crosses it from a stationary point next to the boundary."""
    k = int(np.ceil((lam_still - lam_star) / 0.05)) + 1
    return lam_star + 0.05 * k + 1e-4


def _linear(seed, d):
    rng = np.random.default_rng(seed)
    w = rng.normal(0, 1, d)
    w[np.argmax(np.abs(w))] *= 1.5  # a clear largest coefficient
    return w, 0.0, rng


def test_l2():
    d = 5
    w, b, rng = _linear(11, d)
    X = rng.normal(0, 1, (20, d)) * 0.3
    X = X - ((X @ w + b + rng.uniform(0.3, 1.0, 20))[:, None] / (w @ w)) * w  # z in [-1.0, -0.3]: class 0
    m = LinearTorch(w, b)
    lam0 = lam_schedule_start(0.5 * float(np.linalg.norm(w)), float(np.linalg.norm(w)))
    out, valid, it, ls = W.wachter_batch(m, X, X.copy(), np.full(X.shape, -1e9), np.full(X.shape, 1e9), 1e-3, lam0,
                                         [0, 1], 5000, 2, 200)
    proj = X - ((X @ w + b) / (w @ w))[:, None] * w
    err = float(np.abs(out - proj).max())
    check("Wachter L2: equals the closed-form boundary projection on a linear model, 20 points, <= 1e-3",
          bool(valid.all()) and err <= 1e-3, max_abs_err=err, all_valid=bool(valid.all()))


def test_l1():
    d = 5
    w, b, rng = _linear(12, d)
    cost = rng.uniform(0.5, 2.0, d)
    r = np.abs(w) / cost
    j1 = int(np.argmax(r))
    cost[j1] = np.abs(w[j1]) / (np.sort(r)[-2] / 0.6)  # largest ratio at least 1/0.6 times the second
    X = rng.normal(0, 1, (20, d)) * 0.3
    X = X - ((X @ w + b + rng.uniform(0.3, 1.0, 20))[:, None] / (w @ w)) * w
    m = LinearTorch(w, b)
    jstar = int(np.argmax(np.abs(w) / cost))
    rmax = float(np.max(np.abs(w) / cost))
    lam0 = lam_schedule_start(0.5 * rmax, rmax)
    out, valid, it, ls = W.wachter_batch(m, X, X.copy(), np.full(X.shape, -1e9), np.full(X.shape, 1e9), 2e-4, lam0,
                                         [0, 1], 1000, 1, 200, feature_costs=cost)
    dev = np.abs(out - X)
    others = float(np.delete(dev, jstar, axis=1).max())
    moved = bool((dev[:, jstar] > 1e-2).all())
    check("Wachter L1: only the feature with the largest |w_j|/cost_j changes (others <= 1e-3), 20 points",
          bool(valid.all()) and moved and others <= 1e-3, j_star=jstar, max_other_change=others)


# ---------------------------------------------------------------- BRFSS-layout synthetic problem
def brfss_layout():
    P = C.p7()
    cols = list(P.FT.FEATURE_TAXONOMY.keys())
    order = ["HighBP", "HighChol", "CholCheck", "BMI", "Smoker", "Stroke", "HeartDiseaseorAttack", "PhysActivity",
             "Fruits", "Veggies", "HvyAlcoholConsump", "AnyHealthcare", "NoDocbcCost", "GenHlth", "MentHlth",
             "PhysHlth", "DiffWalk", "Sex", "Age", "Education", "Income"]
    assert set(order) == set(cols)
    lo, span = C.ranges(order)
    return order, lo, span


def synthetic_problem(w_raw, b_raw, xdict, cols, lo, span):
    x = np.array([float(xdict[c]) for c in cols])
    q = pd.Series(x, index=cols)
    grids = {}
    for mode in ("published", "lock"):
        with C.Taxonomy(mode):
            grids[mode] = C.p4_grids(q, cols)
    P = C.p7()
    pred0 = lambda R: (np.atleast_2d(R) @ w_raw + b_raw) < 0  # noqa: E731
    prob0 = lambda R: 1 / (1 + np.exp(np.atleast_2d(R) @ w_raw + b_raw))  # noqa: E731
    return M.Problem(x=x, cols=cols, lo=lo, span=span, grids=grids, predict0=pred0, proba0=prob0,
                     route_ok=lambda ch: bool(P.admissible(list(ch))), lever_parents=C.ada_lever_parents(),
                     patterns=C.route_patterns())


BASE = {"HighBP": 0, "HighChol": 0, "CholCheck": 1, "BMI": 30, "Smoker": 0, "Stroke": 0, "HeartDiseaseorAttack": 0,
        "PhysActivity": 0, "Fruits": 1, "Veggies": 1, "HvyAlcoholConsump": 0, "AnyHealthcare": 1, "NoDocbcCost": 0,
        "GenHlth": 4, "MentHlth": 0, "PhysHlth": 0, "DiffWalk": 0, "Sex": 1, "Age": 9, "Education": 4, "Income": 5}


def indicator_problem():
    """The score depends on GenHlth only, so the only flip is an indicator-only change (GenHlth down one level);
    a gradient method then has no reason to move a lever."""
    cols, lo, span = brfss_layout()
    w = np.zeros(len(cols))
    w[cols.index("GenHlth")] = 2.0
    b = -(2.0 * 4) + 1.0  # z(x) = 1.0 > 0: class 1; GenHlth 4 -> 3 gives z = -1.0
    return synthetic_problem(w, b, BASE, cols, lo, span), w, b, cols, lo, span


def test_mask_projection():
    pb, w, b, cols, lo, span = indicator_problem()
    m = LinearTorch(w, b, lo, span)
    P = len(pb.patterns)
    viol = {"immutable": 0, "range": 0, "forced_lost": 0, "rows": 0}
    for mode in ("published", "lock", "route"):
        rows = M.rows_for_patient(pb, mode, P, seeds=[42])
        feas = [r for r in rows if r["grids"] is not None]
        LO, HI, FX = zip(*[M.box(pb, r["grids"]) for r in feas])
        LO, HI, FX = np.array(LO), np.array(HI), np.array(FX)
        trace = []
        res, valid, it, ls = W.wachter_batch(m, pb.s, np.array([r["start"] for r in feas]), LO, HI, 0.01, 0.01,
                                             [1, 0], 1000, 1, 3, fixed=FX, callback=trace.append)
        s32 = pb.s.astype(np.float32)[None]
        for z in trace:
            viol["immutable"] += int(np.sum(FX & (z != s32)))
            viol["range"] += int(np.sum((z < LO - 1e-6) | (z > HI + 1e-6)))
        viol["rows"] += len(feas)
        if mode == "route":
            for r, s_out in zip(feas, res):
                xr = C.psi(C.to_raw(s_out, lo, span), [r["grids"][f] for f in cols], pb.x)
                for v, u in pb.patterns[r["j"] - 1].items():
                    if u is not None and abs(xr[cols.index(u)] - pb.x[cols.index(u)]) < 1e-9:
                        viol["forced_lost"] += 1
    check("Wachter mask and projection: immutables never change; directions and ranges hold at every iteration; "
          "forced pattern moves survive rounding", viol["immutable"] == 0 and viol["range"] == 0
          and viol["forced_lost"] == 0, **viol)


def test_wallclock():
    m, X = synthetic_ann()
    rng = np.random.default_rng(5)
    x0 = X[:10] + rng.normal(0, 0.01, (10, 6)).astype(np.float32)
    args = (m, X[:10], x0, np.zeros((10, 6)), np.ones((10, 6)), 0.01, 0.01, [1, 0], 200, 1, 2)
    a = W.wachter_batch(*args)
    stop = threading.Event()

    def burn():
        while not stop.is_set():
            sum(i * i for i in range(10000))

    th = [threading.Thread(target=burn, daemon=True) for _ in range(1)]
    real = (time.time, time.perf_counter, time.monotonic)
    jump = [0.0]

    def fake():
        jump[0] += 3600.0
        return real[0]() + jump[0]

    time.time = time.perf_counter = time.monotonic = fake
    try:
        for t in th:
            t.start()
        t0 = real[1]()
        bres = W.wachter_batch(*args)
        slow = real[1]() - t0
    finally:
        stop.set()
        time.time, time.perf_counter, time.monotonic = real
    same = all(np.array_equal(u, v) for u, v in zip(a, bres))
    check("Wachter no wall-clock dependence: identical outputs under artificial CPU load (a busy thread) and a "
          "clock that jumps 1 h per call", same, secs_loaded=slow)


def test_gs():
    """Two-feature linear problem, a third immutable feature: valid, within one step of the boundary, mask kept."""
    gs = V.carla_gs()
    cols = ["a", "b", "c"]
    lo, span = np.zeros(3), np.array([1000.0, 1000.0, 1000.0])  # integer grid, step 0.001 in scaled space
    w = np.array([1.0, 2.0, 5.0]) / 1000.0
    ok_all, gap_max = True, 0.0
    for t in range(10):
        rng = np.random.default_rng(100 + t)
        x = np.array([float(rng.integers(300, 700)), float(rng.integers(300, 700)), 500.0])
        b = -(w @ x) + rng.uniform(0.1, 0.4)
        g = np.arange(0, 1001, dtype=float)
        grids = {"published": {"a": g, "b": g, "c": np.array([x[2]])}}
        pb = M.Problem(x=x, cols=cols, lo=lo, span=span, grids=grids,
                       predict0=lambda R: (np.atleast_2d(R) @ w + b) < 0,
                       proba0=lambda R: 1 / (1 + np.exp(np.atleast_2d(R) @ w + b)), route_ok=lambda ch: True)
        r = gs_res = M.gs_search(pb, "published", 42, gs, binary=[])
        s = pb.s
        dist_boundary = abs(w[:2] @ x[:2] + w[2] * x[2] + b) / np.linalg.norm(w[:2] * span[:2])
        gap = r["l2"] - dist_boundary if r["found"] else np.inf
        gap_max = max(gap_max, gap)
        ok_all &= r["found"] and r["valid_post"] and abs(r["point"][2] - x[2]) < 1e-9 and 0 <= gap <= 0.2 + 1e-6
        del gs_res, s
    check("Growing Spheres: valid, within one step (0.2) of the boundary, mask respected (two-feature linear, "
          "10 factuals)", bool(ok_all), max_gap_over_boundary_distance=gap_max)


def test_ar():
    pb, w, b, cols, lo, span = indicator_problem()
    fs = M.ar_flipset(pb, "published", w, b, size=5)
    # enumerated optimum: all action combinations of up to 3 changed features over the grids, best per support
    G = pb.grids["published"]
    mov = [f for f in cols if len(G[f]) > 1]
    best = {}
    for k in (1, 2, 3):
        for S in itertools.combinations(mov, k):
            vals = [[a for a in G[f] if abs(a - pb.x[cols.index(f)]) > 1e-9] for f in S]
            for combo in itertools.product(*vals):
                z = pb.x.copy()
                for f, a in zip(S, combo):
                    z[cols.index(f)] = a
                if z @ w + b <= -1e-6:
                    c = C.l1_scaled(pb.x, z, span)
                    if frozenset(S) not in best or c < best[frozenset(S)] - 1e-12:
                        best[frozenset(S)] = c
    ref = sorted(best.values())[:5]
    got = [r["cost"] for r in fs]
    eq = len(got) == 5 and np.allclose(sorted(got), ref, atol=1e-9) and all(len(r["changed"]) <= 3 for r in fs)
    check("Actionable Recourse: flipset (size 5) equals the enumerated optimum", bool(eq), mip=got, enumerated=ref)
    fr = M.ar_flipset(pb, "route", w, b, size=5)
    lk = M.ar_flipset(pb, "lock", w, b, size=5)
    ind_only = any(set(r["changed"]) <= set(C.INDICATORS_LOCK) and r["changed"] for r in fr)
    no_leak = all(pb.route_ok(r["changed"]) for r in fr)
    no_ind_lock = all(not (set(r["changed"]) & set(C.INDICATORS_LOCK)) for r in lk)
    check("Actionable Recourse: indicator-only actions excluded under the route constraint (and indicators absent "
          "under the lock)", (not ind_only) and no_leak and no_ind_lock, n_route=len(fr), n_lock=len(lk))


def test_mint():
    rng = np.random.default_rng(3)
    n = 5000
    a = rng.integers(0, 2, n).astype(float)
    bb = 2.0 + 1.5 * a + rng.normal(0, 0.5, n)
    c = -1.0 + 0.8 * bb + rng.normal(0, 0.5, n)
    df = pd.DataFrame({"a": a, "b": bb, "c": c})
    scm = M.LinearSCM.fit(df, [("a", "b"), ("b", "c")])
    x = {"a": 0.0, "b": 2.7, "c": 1.4}
    ident = lambda f, v: v  # noqa: E731
    new = scm.counterfactual(x, {"a": 1.0}, ident)
    b0, b1 = scm.coef["b"]
    c0, c1 = scm.coef["c"]
    exp_b = x["b"] + b1[0] * 1.0
    exp_c = x["c"] + c1[0] * (exp_b - x["b"])
    ok1 = abs(new["b"] - exp_b) < 1e-9 and abs(new["c"] - exp_c) < 1e-9
    # rounding: a parent change that rounds to zero leaves the child unchanged
    rnd = lambda f, v: float(np.round(v)) if f == "b" else v  # noqa: E731
    x2 = {"a": 0.0, "b": 3.0, "c": 1.4}
    scm.coef["b"] = (b0, np.array([0.3]))
    new2 = scm.counterfactual(x2, {"a": 1.0}, rnd)
    ok2 = new2["b"] == 3.0 and new2["c"] == 1.4
    check("MINT: abduction-action-prediction = closed form on (a, b), (b, c); a parent change that rounds to zero "
          "leaves the child unchanged", ok1 and ok2, b=new["b"], c=new["c"], exp_b=exp_b, exp_c=exp_c)


def test_route_all_methods():
    pb, w, b, cols, lo, span = indicator_problem()
    m = LinearTorch(w, b, lo, span)
    P = len(pb.patterns)
    out = {}
    # Wachter
    for mode in ("published", "route"):
        rows = M.rows_for_patient(pb, mode, P)
        res = M.wachter_rows(m, [pb], [rows])[0]
        recs = M.finish_rows(pb, rows, res, mode)
        kept = [r for r in recs if r.get("kept")]
        out[f"wachter_{mode}"] = [(r["changed"], pb.route_ok(r["changed"].split(";") if r["changed"] else [])) for r in kept]
    # Growing Spheres
    gs = V.carla_gs()
    for mode in ("published", "route"):
        rs = [M.gs_search(pb, mode, s, gs) for s in C.SEEDS]
        out[f"gs_{mode}"] = [(";".join(C.change_set(pb.x, r["point"], cols)),
                              pb.route_ok(C.change_set(pb.x, r["point"], cols))) for r in rs if r["found"]]
    # AR
    for mode in ("published", "route"):
        fs = M.ar_flipset(pb, mode, w, b)
        out[f"ar_{mode}"] = [(";".join(r["changed"]), pb.route_ok(r["changed"])) for r in fs]
    pub_leaks = {k: any(not ok for _, ok in v) for k, v in out.items() if k.endswith("published")}
    route_ok = {k: all(ok for _, ok in v) for k, v in out.items() if k.endswith("route")}
    check("Route constraint (Wachter, Growing Spheres, AR): a patient whose only cheap flip is indicator-only leaks "
          "in published mode and is supported or empty in route-aware mode",
          all(pub_leaks.values()) and all(route_ok.values()), published_leaks=pub_leaks, route_all_supported=route_ok,
          examples={k: v[:2] for k, v in out.items()})


def _turtle_brfss():
    from depgraph.edges import EDGES
    T = C.roles()
    KG = "https://github.com/thieuanhvan/diabetes-xai-dependencygraph/kg#"
    lines = [f"@prefix kg: <{KG}> .", ""]
    for f, r in sorted(T.items()):
        lines.append(f"kg:ra_{f}_T2D a kg:RoleAssignment ; kg:ofVariable kg:{f} ; kg:assignedIn kg:T2D ; kg:role kg:{r} .")
    for j, e in enumerate(EDGES):
        g = "true" if e.grade in ("A", "B", "C", "E") else "false"
        lines.append(f"kg:st{j} a kg:Statement ; kg:subject kg:{e.src} ; kg:object kg:{e.dst} ; kg:authority kg:ADA ; "
                     f"kg:graded {g} .")
    return KG, "\n".join(lines) + "\n"


def test_sparql():
    import random
    import rdflib
    KG, ttl = _turtle_brfss()
    g = rdflib.Graph()
    g.parse(data=ttl, format="turtle")
    (C.OUT / "unit_tests").mkdir(parents=True, exist_ok=True)
    (C.OUT / "unit_tests" / "brfss_t2d_graph.ttl").write_text(ttl, encoding="utf-8", newline="\n")
    P = C.p7()
    D = C.stats()
    from depgraph.edges import EDGES
    T = C.roles()
    E_all = {(e.src, e.dst) for e in EDGES}
    E_gr = {(e.src, e.dst) for e in EDGES if e.grade in ("A", "B", "C", "E")}

    def sel(q):
        return {str(r[0]).split("#")[1] for r in g.query(f"PREFIX kg: <{KG}> SELECT DISTINCT ?v WHERE {{ {q} }}")}

    def ask(S, graded, k, strict):
        """SPARQL: indicators in S minus those with a lever in S on a path of <= k Statements (intermediate
        treatable, and in S when strict); leaks if non-empty. Membership of S is asserted as temporary triples."""
        gf = "kg:graded true ;" if graded else ""
        role = lambda v, r: f"?r{v[1:]} kg:ofVariable {v} ; kg:assignedIn kg:T2D ; kg:role kg:{r} ."  # noqa: E731
        for f in S:
            g.add((rdflib.URIRef(KG + f), rdflib.URIRef(KG + "inS"), rdflib.Literal(True)))
        try:
            ind = sel(f"?v kg:inS true . {role('?v', 'indicator')}")
            sup = sel(f"?v kg:inS true . ?s0 {gf} kg:object ?v ; kg:subject ?u . ?u kg:inS true . {role('?u', 'lever')}")
            if k >= 2:
                ins = "?t kg:inS true ." if strict else ""
                sup |= sel(f"?v kg:inS true . ?s2 {gf} kg:object ?v ; kg:subject ?t . {role('?t', 'treatable')} {ins} "
                           f"?s1 {gf} kg:object ?t ; kg:subject ?u . ?u kg:inS true . {role('?u', 'lever')}")
            return bool(ind - sup)
        finally:
            for f in S:
                g.remove((rdflib.URIRef(KG + f), rdflib.URIRef(KG + "inS"), rdflib.Literal(True)))

    rng = random.Random(20261111)
    mov = sorted(f for f in T if f not in ("Age", "Sex", "Stroke", "HeartDiseaseorAttack"))
    res, allok = {}, True
    readings = {"ada_k1_P7admissible": (False, 1, False), "ada_graded_k1": (True, 1, False),
                "ada_k2_permissive": (False, 2, False), "ada_k2_strict": (False, 2, True)}
    for name, (graded, k, strict) in readings.items():
        dis, memo, nleak = 0, {}, 0
        for _ in range(10_000):
            S = set(rng.sample(mov, rng.randint(1, 5)))
            if name == "ada_k1_P7admissible":
                py = not P.admissible(sorted(S))
            else:
                E = E_gr if graded else E_all
                py = any(not D.supported(v, S, E, k, strict, role=T) for v in S if T.get(v) == "indicator")
            key = frozenset(S)
            if key not in memo:
                memo[key] = ask(S, graded, k, strict)
            dis += py != memo[key]
            nleak += py
        res[name] = {"n_sets": 10_000, "distinct": len(memo), "disagreements": dis, "python_leaking": nleak}
        allok &= dis == 0
    check("Path constraint: Python and SPARQL agree on 10,000 random change sets (4 readings, BRFSS ADA graph)",
          allok, **res)


def test_null():
    D = C.stats()
    rng = np.random.default_rng(1)
    ok = True
    for _ in range(50):
        m = int(rng.integers(3, 8))
        Mv = [f"f{j}" for j in range(m)]
        n_ind = int(rng.integers(1, 4))
        n_ind = min(n_ind, m)
        cnt = {f: int(rng.integers(0, 6)) for f in Mv}
        ex = Counter(np.round(D.patient_null(cnt, Mv, n_ind), 12))
        bf = Counter()
        for perm in itertools.permutations(range(m)):
            bf[round(D.oshare(cnt, [Mv[i] for i in perm[:n_ind]]), 12)] += 1
        tot, tex = sum(bf.values()), sum(ex.values())
        ok &= all(abs(ex[v] / tex - bf[v] / tot) < 1e-12 for v in set(bf) | set(ex))
    check("Movability null: exact per-patient enumeration = brute force (50 toy patients, up to 3 indicators)", ok)
    # uniformity under a generator that changes movable features uniformly at random
    from scipy.stats import kstest
    rng = np.random.default_rng(20261111)
    ps = []
    for c in range(1000):
        obs, nulls = [], []
        for i in range(30):
            m = int(rng.integers(4, 12))
            Mv = [f"f{j}" for j in range(m)]
            n_ind = int(rng.integers(0, 4))
            inds = Mv[:n_ind]
            cnt = Counter()
            for _ in range(5):
                k = int(rng.integers(1, min(4, m) + 1))
                for f in rng.choice(Mv, size=k, replace=False):
                    cnt[str(f)] += 1
            obs.append(D.oshare(cnt, inds))
            nulls.append(D.patient_null(cnt, Mv, n_ind))
        T, p, _ = D.movability_null_p(obs, nulls, draws=2000, seed=int(rng.integers(0, 2**31)))
        ps.append(p)
    ks = kstest(ps, "uniform")
    check("Movability null: p uniform under a uniformly random generator (1,000 toy cohorts, 2,000 draws each; "
          "KS p > 0.01)", ks.pvalue > 0.01, ks_stat=float(ks.statistic), ks_p=float(ks.pvalue),
          mean_p=float(np.mean(ps)))


TESTS = [test_vendor, test_parity, test_l2, test_l1, test_mask_projection, test_wallclock, test_gs, test_ar,
         test_mint, test_route_all_methods, test_sparql, test_null]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    C.below_normal()
    sel = [t for t in TESTS if not a.only or t.__name__ in a.only.split(",")]
    t0 = time.time()
    for t in sel:
        try:
            t()
        except Exception as e:  # a crash is a failure
            import traceback
            traceback.print_exc()
            check(t.__name__ + " (crashed)", False, error=repr(e))
    summ = {"tests": RESULTS, "failed": FAILED, "all_pass": not FAILED, "secs": time.time() - t0,
            "subset": a.only or "all", "torch": torch.__version__}
    if not a.only:
        C.write_json(C.OUT / "unit_tests" / "test_b_results.json", summ)
    print("ALL PASS" if not FAILED else f"FAILED: {FAILED}", flush=True)
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
