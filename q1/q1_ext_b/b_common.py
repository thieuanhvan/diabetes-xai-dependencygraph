"""P7 Q1 extension B (prereg v3 section 5, 11/11/2026 16:45): shared objects for runs, analysis and tests.

- Data, split and P4 taxonomy: the P7 loader `p7_cross_p4pipeline.load("brfss2021")`, split 80/20 stratified,
  seed 42; the P4 taxonomy is patched in memory only (lock mode = GenHlth, PhysHlth, MentHlth immutable, as P7
  tableV). Nothing is written into the P4 or P7 repositories.
- Scaling (prereg 5.3): s = (x - lo) / (hi - lo) with the P4 value range of each feature. Distances (L1 for
  Wachter, AR and the exhaustive search; L2 for Growing Spheres) are computed in this scaled space.
- Admissible grid G_f(x) of a feature for one patient and mode: {x_f} plus the integer grid of the P4 permitted
  range (P7 exhaustive-search grid) when f is in the P4 features_to_vary of the query; {x_f} otherwise. A forced
  lever of a route pattern has G restricted to values at least one grid step from x_f in its permitted direction.
- Rounding psi (prereg 5.3, once at the end): each feature goes to the nearest element of G_f (tie: the element
  nearer to x_f). The change set then follows the P7 change rule (all BRFSS values are integers after psi).
- Roles, audit and the path constraint: depgraph (nodes.TIER, edges.EDGES, audit.classify) and P7's
  `admissible` (k = 1, lever sources, all ADA edges), unchanged.
- Route patterns (prereg 5.3): each indicator is locked, or free with one ADA lever parent forced; on BRFSS
  diabetes 3 x 4 x 2 = 24 patterns (DiffWalk is immovable).
- Statistics: the frozen A2 helpers (a2_domain: per-patient movability null, bootstrap, Clopper-Pearson, trunc)
  are imported, so extension B uses the same code as extension A.
Run every script with `python -I` in the p7-carla312 venv.
"""
from __future__ import annotations

import ctypes
import hashlib
import itertools
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# BLAS limited to 2 threads (prereg 5.7). OMP_NUM_THREADS is NOT set: XGBoost keeps the P4 configuration (n_jobs -1,
# all cores), and an OpenMP limit changes the fitted XGBoost model (bug B-E3); torch threads are set explicitly.
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(TOOLS / "crossdataset_p4"))
sys.path.insert(0, str(TOOLS / "q1_domain_ckd"))
sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

PAPER7 = Path("D:/20-study/uit/research/diabetesxai/paper7")
PREREG = PAPER7 / "prereg" / "prereg_q1_extension_en_v3_20261111_1645.md"
PREREG_SHA256 = "95a83da578b975f5e578139182f51113020ff9fefcff927a037742b4a112369d"
OUT = PAPER7 / "outputs" / "q1_ext_b"
SEEDS = [42, 123, 2024, 7, 31337]
TARGET = "Diabetes_binary"
DESIRED = 0
INDICATORS_LOCK = ["GenHlth", "PhysHlth", "MentHlth"]  # BRFSS lock set (prereg 2)


def below_normal() -> None:
    """Machine rule: heavy Python at below-normal priority."""
    if os.name == "nt":
        h = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.kernel32.SetPriorityClass(h, 0x00004000)


def check_prereg() -> None:
    h = sha256_file(PREREG)
    if h != PREREG_SHA256:
        sys.exit(f"prereg hash mismatch: {h}")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=float) + "\n", encoding="utf-8")


def trunc(x, nd: int = 4) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "NA"
    f = 10 ** nd
    return f"{math.trunc(x * f) / f:.{nd}f}"


# ---------------------------------------------------------------------------------------------- P7 objects
def p7():
    """The P7 pipeline module (loader, taxonomy, admissible). Imported lazily: it pulls in the P4 repository."""
    import p7_cross_p4pipeline as P  # noqa: WPS433
    return P


def roles():
    from depgraph.nodes import TIER  # noqa: WPS433
    return TIER


def ada_lever_parents() -> Dict[str, List[str]]:
    """Lever parents of each indicator in the ADA graph (k = 1 sources of P7's admissible())."""
    from depgraph.edges import EDGES  # noqa: WPS433
    T = roles()
    out: Dict[str, List[str]] = {}
    for e in EDGES:
        if T.get(e.dst) == "indicator" and T.get(e.src) == "lever":
            out.setdefault(e.dst, [])
            if e.src not in out[e.dst]:
                out[e.dst].append(e.src)
    return {k: sorted(v) for k, v in out.items()}


def route_patterns(movable_indicators: Sequence[str] = ("GenHlth", "PhysHlth", "MentHlth")) -> List[Dict[str, Optional[str]]]:
    """All patterns: indicator -> None (locked) or the forced lever parent. Fixed order (j = 1..P)."""
    par = ada_lever_parents()
    choices = [[None] + par.get(v, []) for v in movable_indicators]
    return [dict(zip(movable_indicators, c)) for c in itertools.product(*choices)]


def load_brfss():
    """X (21 features, P7/P4 column order), y, train/test split exactly as P7 (seed 42, 80/20, stratified)."""
    P = p7()
    X, y, _ = P.load("brfss2021")
    Xtr, Xte, ytr, yte = P.get_train_test_split(X, y, test_size=P.CFG["split"]["test_size"],
                                                seed=P.CFG["random"]["seed"], stratify=P.CFG["split"]["stratify"])
    return X, y, Xtr, Xte, ytr, yte


def ranges(cols: Sequence[str]) -> Tuple[np.ndarray, np.ndarray]:
    FT = p7().FT
    lo = np.array([float(FT.FEATURE_TAXONOMY[c].value_range[0]) for c in cols])
    hi = np.array([float(FT.FEATURE_TAXONOMY[c].value_range[1]) for c in cols])
    return lo, np.maximum(hi - lo, 1e-9)


def to_scaled(Xraw: np.ndarray, lo: np.ndarray, span: np.ndarray) -> np.ndarray:
    return (np.asarray(Xraw, dtype=float) - lo) / span


def to_raw(S: np.ndarray, lo: np.ndarray, span: np.ndarray) -> np.ndarray:
    return lo + np.asarray(S, dtype=float) * span


def cohort(proba: np.ndarray, n: int = 200) -> np.ndarray:
    """P7 rule: test patients with p >= 0.5, at most the n highest-risk (positions in the test split)."""
    elig = np.where(proba >= 0.5)[0]
    return elig[np.argsort(proba[elig], kind="stable")][-min(n, len(elig)):]


# ------------------------------------------------------------------------------------- grids and rounding
class Taxonomy:
    """Context manager: P4 taxonomy with the lock set immutable (P7 tableV) for mode 'lock'."""

    def __init__(self, mode: str):
        self.mode = mode

    def __enter__(self):
        P = p7()
        self.saved = {f: P.FT.FEATURE_TAXONOMY[f] for f in P.TABLE_V}
        if self.mode == "lock":
            for f, s in self.saved.items():
                P.FT.FEATURE_TAXONOMY[f] = P.FeatureSpec(f, P.Mutability.IMMUTABLE, s.value_range, s.semantic_label)
        return self

    def __exit__(self, *exc):
        P = p7()
        for f, s in self.saved.items():
            P.FT.FEATURE_TAXONOMY[f] = s


def p4_grids(q: pd.Series, cols: Sequence[str]) -> Dict[str, np.ndarray]:
    """G_f(x) under the CURRENT taxonomy: {x_f} plus the P7 integer grid of the permitted range for f in
    features_to_vary; {x_f} otherwise."""
    FT = p7().FT
    ftv = set(FT.get_features_to_vary_for_query(q))
    perm = FT.get_permitted_range_for_query(q)
    out = {}
    for f in cols:
        cur = float(q[f])
        if f in ftv:
            lo, hi = perm[f]
            g = np.arange(np.ceil(lo), np.floor(hi) + 1)
            out[f] = np.unique(np.concatenate([g, [cur]]))
        else:
            out[f] = np.array([cur])
    return out


def movable(grids: Dict[str, np.ndarray], q: pd.Series) -> List[str]:
    """Prereg 4.7: f is movable when A*_f(x_f) contains a value other than x_f."""
    return [f for f, g in grids.items() if np.any(np.abs(g - float(q[f])) > 1e-9)]


def forced_grid(f: str, q: pd.Series, g: np.ndarray, side: Optional[int] = None) -> np.ndarray:
    """Values of G_f at least one grid step from x_f in the permitted direction (side +1 up, -1 down; for a
    bidirectional lever the side is given by the caller)."""
    FT = p7().FT
    cur = float(q[f])
    mut = FT._effective_mutability(FT.FEATURE_TAXONOMY[f]).value
    if mut == "monotonic_up":
        side = +1
    elif mut == "monotonic_down":
        side = -1
    elif side is None:
        raise ValueError(f"side needed for {f}")
    return g[g >= cur + 1 - 1e-9] if side > 0 else g[g <= cur - 1 + 1e-9]


def psi(raw: np.ndarray, grids: Sequence[np.ndarray], x: np.ndarray) -> np.ndarray:
    """Rounding to the admissible grid: nearest element of G_f per feature; ties go to the element nearer x_f.
    raw: (n, d) or (d,)."""
    R = np.atleast_2d(np.asarray(raw, dtype=float))
    out = np.empty_like(R)
    for j, g in enumerate(grids):
        d = np.abs(R[:, j:j + 1] - g[None, :])
        tie = np.abs(g - x[j])[None, :] * 1e-9  # tie-break toward x_f
        out[:, j] = g[np.argmin(d + tie, axis=1)]
    return out if np.ndim(raw) == 2 else out[0]


def change_set(x: np.ndarray, xc: np.ndarray, cols: Sequence[str]) -> List[str]:
    """P7 change rule: discrete features compared after int rounding; BMI changed when |diff| > 1e-6."""
    out = []
    for j, f in enumerate(cols):
        b, c = float(x[j]), float(xc[j])
        moved = abs(b - c) > 1e-6 if f == "BMI" else int(round(b)) != int(round(c))
        if moved:
            out.append(f)
    return out


def l1_scaled(x: np.ndarray, xc: np.ndarray, span: np.ndarray) -> float:
    return float(np.sum(np.abs(np.asarray(xc, float) - np.asarray(x, float)) / span))


def audit(changed: Sequence[str]) -> dict:
    """P7 audit (depgraph.audit.classify, narrow reading, edge rule) plus P7's route admissibility."""
    from depgraph.audit import classify  # noqa: WPS433
    c = classify(changed, reading="narrow", rule="edge")
    T = roles()
    return {"touches": c["touches_target"], "leaks": c["unsupported"], "fully_unactionable": c["fully_unactionable"],
            "n_indicator_changes": sum(T.get(f) == "indicator" for f in changed), "n_changes": len(changed),
            "route_ok": bool(p7().admissible(list(changed)))}


def stats():
    """The frozen A2 statistics helpers (movability null, bootstrap, Clopper-Pearson)."""
    import a2_domain as D  # noqa: WPS433
    return D
