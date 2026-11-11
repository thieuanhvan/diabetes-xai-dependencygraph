"""Generator ports for extension B (prereg v3 5.3), shared by the run scripts and the unit tests.

All methods work in the scaled space s = (x - lo) / span (P4 ranges) and round once at the end with psi onto the
admissible grid of the mode (b_common). A method is given a `Problem`: the factual, its grids per mode, the model
callables and the route rule.

Wachter (5.3, equal search effort): per seed P runs; published and lock use P random starts s(x) + N(0, 0.01^2)
from numpy default_rng(seed * 1000 + j), j = 1..P; route-aware uses one run per pattern j with the same sub-seed.
Pattern rows: a locked indicator has G = {x}; a free indicator keeps its P4 grid and its forced lever has G
restricted to values at least one grid step away in the permitted direction (bidirectional BMI: the side whose
nearest forced grid value gives the higher class-0 probability; ties go down). A pattern whose forced lever has no
such value is infeasible for that patient and yields no output (clarification B-C2). The kept output of a seed is
the valid rounded result of lowest scaled L1 cost (ties: lowest j); route-aware results must also pass the path
constraint after rounding.

Growing Spheres (5.3): the vendored CARLA sampler `hyper_sphere_coordindates` (unedited) for the mutable
non-binary features and Bernoulli(0.5) for the mutable binary features, as CARLA's growing_spheres_search, with two
edits (deviation log B-D3): feature lists are sorted (CARLA iterates Python sets, whose order depends on the string
hash seed, so runs were not reproducible), and candidates are rounded, then rejected when the plain integer rounding
of a feature leaves its admissible grid (directions, ranges, mask) or, in route-aware mode, when the change set
fails the path constraint; the nearest valid rounded candidate (scaled L2) of the first layer that has one is kept.
CARLA defaults: 1,000 samples per layer, step 0.2, max 1,000 layers. np.random.seed(seed) per patient and seed.

Actionable Recourse (5.3): the integer program of Ustun et al. (2019) solved with python-mip/CBC on the LR score
(linear in the raw features): one binary per (feature, grid action), at most one action per feature, score <= -1e-6
(class 0), objective = scaled L1 cost; flipset of size 5 by successive no-good cuts on the set of changed features
(the flipset enumeration of the AR paper). Lock: indicator actions removed. Route: z_v <= sum of z_u over the ADA
lever parents u of v. The `recourse` package and CARLA's LIME wrapper are not used (deviation log B-D4).

MINT (5.3, illustration of Proposition 2 only): linear additive-noise SCM on the ADA graph restricted to BRFSS
features, OLS on the training split; abduction; interventions on at most three movable levers with values from
the P4 grids, brute force at minimum scaled L1 action cost (ties: fewer interventions, then order of enumeration);
topological rounding (A7: a node is recomputed from rounded parents, then rounded to the integer grid of its P4
range, extended to the factual value; an un-intervened node with unchanged parents keeps its value).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

import b_common as C
import b_wachter_core as W

WACHTER = {"lr": 0.01, "lambda_param": 0.01, "n_iter": 1000, "norm": 1, "max_lambda_steps": 10,
           "y_target": [1, 0], "start_sd": 0.01}


@dataclass
class Problem:
    """One factual x (raw, (d,)), feature names, P4 scaling, grids per mode and the model."""
    x: np.ndarray
    cols: List[str]
    lo: np.ndarray
    span: np.ndarray
    grids: Dict[str, Dict[str, np.ndarray]]          # mode ('published' | 'lock') -> feature -> G_f
    predict0: Callable[[np.ndarray], np.ndarray]      # raw (n, d) -> bool, predicted class 0
    proba0: Callable[[np.ndarray], np.ndarray]        # raw (n, d) -> P(class 0)
    route_ok: Callable[[Sequence[str]], bool]
    lever_parents: Dict[str, List[str]] = field(default_factory=dict)
    patterns: List[Dict[str, Optional[str]]] = field(default_factory=list)

    @property
    def s(self) -> np.ndarray:
        return C.to_scaled(self.x, self.lo, self.span)


# -------------------------------------------------------------------------------------------------- Wachter
def pattern_grids(pb: Problem, pattern: Dict[str, Optional[str]]) -> Optional[Dict[str, np.ndarray]]:
    """Grids of one route pattern, or None when a forced lever cannot move (pattern infeasible)."""
    import pandas as pd
    G = {f: g.copy() for f, g in pb.grids["published"].items()}
    q = pd.Series(pb.x, index=pb.cols)
    forced = sorted({u for u in pattern.values() if u is not None})
    for v, u in pattern.items():
        if u is None:
            G[v] = np.array([float(q[v])])
    for u in forced:
        g = pb.grids["published"][u]
        if u == "BMI":
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
            cand.sort(key=lambda t: (t[0], t[1]))  # higher class-0 probability first; tie -> down (-1)
            G[u] = cand[0][2]
        else:
            fg = C.forced_grid(u, q, g)
            if not len(fg):
                return None
            G[u] = fg
    return G


def rows_for_patient(pb: Problem, mode: str, P: int, seeds: Sequence[int] = C.SEEDS):
    """Row specifications (seed, j, grids, start) for one patient and mode; infeasible route rows have grids None."""
    rows = []
    d = len(pb.cols)
    for seed in seeds:
        for j in range(1, P + 1):
            if mode == "route":
                G = pattern_grids(pb, pb.patterns[j - 1])
            else:
                G = pb.grids[mode]
            start = pb.s + np.random.default_rng(seed * 1000 + j).normal(0.0, WACHTER["start_sd"], d)
            rows.append({"seed": seed, "j": j, "grids": G, "start": start})
    return rows


def box(pb: Problem, G: Dict[str, np.ndarray]):
    lo = np.array([(G[f].min() - pb.lo[i]) / pb.span[i] for i, f in enumerate(pb.cols)])
    hi = np.array([(G[f].max() - pb.lo[i]) / pb.span[i] for i, f in enumerate(pb.cols)])
    # fixed = held at the factual value; a forced lever with a single admissible value (e.g. PhysActivity 0 -> 1) is
    # not fixed but clamped to that value by lo = hi
    fixed = np.array([len(G[f]) == 1 and abs(float(G[f][0]) - pb.x[i]) < 1e-9 for i, f in enumerate(pb.cols)])
    return lo, hi, fixed


def wachter_rows(torch_model, problems: Sequence[Problem], rowsets: Sequence[list], params=WACHTER):
    """Run all feasible rows of several patients in one batch. Returns, per patient, a list of row results."""
    X, X0, LO, HI, FX, owner = [], [], [], [], [], []
    for pi, (pb, rows) in enumerate(zip(problems, rowsets)):
        for ri, r in enumerate(rows):
            if r["grids"] is None:
                continue
            lo, hi, fx = box(pb, r["grids"])
            X.append(pb.s)
            X0.append(r["start"])
            LO.append(lo)
            HI.append(hi)
            FX.append(fx)
            owner.append((pi, ri))
    out = [[None] * len(rows) for rows in rowsets]
    if X:
        res, valid, iters, lsteps = W.wachter_batch(torch_model, np.array(X), np.array(X0), np.array(LO), np.array(HI),
                                                    params["lr"], params["lambda_param"], params["y_target"],
                                                    params["n_iter"], params["norm"], params["max_lambda_steps"],
                                                    fixed=np.array(FX))
        for k, (pi, ri) in enumerate(owner):
            out[pi][ri] = {"s_out": res[k], "valid_pre": bool(valid[k]), "iters": int(iters[k]), "lsteps": int(lsteps[k])}
    return out


def finish_rows(pb: Problem, rows: list, results: list, mode: str) -> List[dict]:
    """Round, audit and select the kept output per seed. Returns one record per row (kept flag set)."""
    recs = []
    for r, res in zip(rows, results):
        rec = {"seed": r["seed"], "j": r["j"], "feasible": res is not None}
        if res is None:
            rec.update(valid_pre=False, valid_post=False, route_ok=False, cost=np.nan, changed="", iters=0, lsteps=0,
                       point=None)
            recs.append(rec)
            continue
        raw = C.to_raw(res["s_out"], pb.lo, pb.span)
        grids = [r["grids"][f] for f in pb.cols]
        xr = C.psi(raw, grids, pb.x)
        ch = C.change_set(pb.x, xr, pb.cols)
        rec.update(valid_pre=res["valid_pre"], valid_post=bool(pb.predict0(xr[None])[0]),
                   route_ok=bool(pb.route_ok(ch)), cost=C.l1_scaled(pb.x, xr, pb.span), changed=";".join(ch),
                   iters=res["iters"], lsteps=res["lsteps"], point=xr)
        recs.append(rec)
    for seed in sorted({r["seed"] for r in recs}):
        cand = [r for r in recs if r["seed"] == seed and r["valid_post"] and (mode != "route" or r["route_ok"])]
        for r in recs:
            if r["seed"] == seed:
                r["kept"] = False
        if cand:
            best = min(cand, key=lambda r: (r["cost"], r["j"]))
            best["kept"] = True
    return recs


# ---------------------------------------------------------------------------------------- Growing Spheres
def gs_search(pb: Problem, mode: str, seed: int, gs_mod, n_search_samples=1000, step=0.2, max_iter=1000,
              binary: Optional[Sequence[str]] = None):
    """One Growing Spheres output for pb in mode ('published' | 'lock' | 'route'). Returns a dict."""
    G = pb.grids["lock" if mode == "lock" else "published"]
    cols = pb.cols
    keys_mutable = sorted(f for f in cols if len(G[f]) > 1)
    keys_immutable = sorted(f for f in cols if len(G[f]) == 1)
    binary = set(binary if binary is not None else [f for f in cols if set(np.unique(G[f])) <= {0.0, 1.0}
                                                    and (pb.lo[cols.index(f)], pb.lo[cols.index(f)] + pb.span[cols.index(f)]) == (0.0, 1.0)])
    keys_cont = sorted(set(keys_mutable) - binary)
    keys_bin = sorted(set(keys_mutable) & binary)
    pos = {f: i for i, f in enumerate(cols)}
    s = pb.s
    grids = [G[f] for f in cols]
    np.random.seed(seed)
    low, high, count = 0.0, step, 0
    n_eval = 0
    while count < max_iter:
        count += 1
        cand = np.repeat(s[None, :], n_search_samples, axis=0)
        if keys_cont:
            inst = s[[pos[f] for f in keys_cont]].reshape(1, -1)
            cc, _ = gs_mod.hyper_sphere_coordindates(n_search_samples, inst, high, low, 2)
            cand[:, [pos[f] for f in keys_cont]] = cc
        if keys_bin:
            cb = np.random.binomial(n=1, p=0.5, size=n_search_samples * len(keys_bin)).reshape(n_search_samples, -1)
            cand[:, [pos[f] for f in keys_bin]] = cb
        raw = C.to_raw(cand, pb.lo, pb.span)
        free = np.round(raw)
        keep = np.ones(n_search_samples, bool)
        for j, f in enumerate(cols):
            keep &= np.isin(free[:, j], G[f])
        idx = np.where(keep)[0]
        if len(idx):
            xr = C.psi(raw[idx], grids, pb.x)
            ok = pb.predict0(xr)
            n_eval += len(idx)
            if mode == "route":
                ok &= np.array([pb.route_ok(C.change_set(pb.x, z, cols)) for z in xr])
            if ok.any():
                sr = C.to_scaled(xr, pb.lo, pb.span)
                dist = np.sqrt(((sr - s) ** 2).sum(axis=1))
                dist[~ok] = np.inf
                k = int(np.argmin(dist))
                pre = bool(pb.predict0(raw[idx][k:k + 1])[0])
                return {"found": True, "point": xr[k], "valid_pre": pre, "valid_post": True, "layers": count,
                        "l2": float(dist[k]), "n_eval": n_eval}
        low, high = high, high + step
    return {"found": False, "point": None, "valid_pre": False, "valid_post": False, "layers": count, "l2": np.nan,
            "n_eval": n_eval}


# ------------------------------------------------------------------------------------- Actionable Recourse
def ar_flipset(pb: Problem, mode: str, w_raw: np.ndarray, b_raw: float, size: int = 5, eps: float = 1e-6,
               indicators: Sequence[str] = C.INDICATORS_LOCK) -> List[dict]:
    """Flipset of up to `size` actions for the linear score z(x) = w_raw . x + b_raw (class 0 iff z < 0)."""
    import mip
    G = pb.grids["lock" if mode == "lock" else "published"]
    cols, x = pb.cols, pb.x
    z0 = float(w_raw @ x + b_raw)
    m = mip.Model(sense=mip.MINIMIZE, solver_name="CBC")
    m.verbose = 0
    m.threads = 1
    acts: Dict[str, List[Tuple[float, "mip.Var"]]] = {}
    zf = {}
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
    m.objective = mip.xsum(abs(a - x[i]) / pb.span[i] * u for i, f in enumerate(cols) for a, u in acts[f])
    out = []
    for _ in range(size):
        st = m.optimize()
        if st not in (mip.OptimizationStatus.OPTIMAL,):
            break
        xc = x.copy()
        S = []
        for i, f in enumerate(cols):
            for a, u in acts[f]:
                if u.x is not None and u.x > 0.5:
                    xc[i] = a
                    S.append(f)
        out.append({"point": xc, "changed": C.change_set(x, xc, cols), "cost": C.l1_scaled(x, xc, pb.span),
                    "score": float(w_raw @ xc + b_raw)})
        if not S:
            break
        m += mip.xsum(zf[f] for f in S) - mip.xsum(zf[f] for f in zf if f not in S) <= len(S) - 1
    return out


# -------------------------------------------------------------------------------------------------- MINT
@dataclass
class LinearSCM:
    order: List[str]                         # topological order of the nodes with parents
    parents: Dict[str, List[str]]
    coef: Dict[str, Tuple[float, np.ndarray]]  # child -> (intercept, coefficients over parents)

    @staticmethod
    def fit(Xtr, edges: Sequence[Tuple[str, str]]) -> "LinearSCM":
        par: Dict[str, List[str]] = {}
        for a, b in sorted(set(edges)):
            par.setdefault(b, []).append(a)
        nodes = set(par) | {a for a, _ in edges}
        order, done = [], {n for n in nodes if n not in par}
        while len(done) < len(nodes):
            nxt = sorted(n for n in par if n not in done and all(p in done for p in par[n]))
            if not nxt:
                raise ValueError("graph has a cycle")
            order += nxt
            done |= set(nxt)
        coef = {}
        for c in order:
            A = np.c_[np.ones(len(Xtr)), Xtr[par[c]].to_numpy(float)]
            beta, *_ = np.linalg.lstsq(A, Xtr[c].to_numpy(float), rcond=None)
            coef[c] = (float(beta[0]), beta[1:])
        return LinearSCM(order, par, coef)

    def counterfactual(self, x: Dict[str, float], do: Dict[str, float], rounder: Callable[[str, float], float]):
        """Abduction (noise = x_c - fitted), action, prediction with topological rounding (A7)."""
        new = dict(x)
        new.update(do)
        changed = {f for f in do if abs(do[f] - x[f]) > 1e-9}
        for c in self.order:
            if c in do:
                continue
            ps = self.parents[c]
            if not any(p in changed for p in ps):
                continue
            b0, b = self.coef[c]
            noise = x[c] - (b0 + float(b @ np.array([x[p] for p in ps])))
            val = rounder(c, b0 + float(b @ np.array([new[p] for p in ps])) + noise)
            if abs(val - x[c]) > 1e-9:
                new[c] = val
                changed.add(c)
        return new
