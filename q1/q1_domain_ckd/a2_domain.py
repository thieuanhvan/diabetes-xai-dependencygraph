"""P7 Q1 step A2: CKD domain objects shared by the run and analysis scripts (prereg v3, 11/11/2026 16:45).

- Roles, directions and lock set: read from the frozen A0 role table (a0_role_table/), never re-derived here.
- Edges: KDIGO = the agreed (intersection) graph of step A1 mapped to NHANES items; ADA = depgraph.edges.EDGES
  restricted to CKD items (the "other domain" authority for A-Q4 and the union reading).
- Path constraint (prereg 3): accept(S) iff every indicator v in S has a lever u in S with a directed path
  u -> ... -> v of at most k edges, every edge in the authority/strength filter, every intermediate node
  treatable in the domain (strict variant: intermediates also in S).
- Movability (prereg 4.7, O-A2): feature f is movable for patient x when the P4 per-query permitted set
  A*_f(x_f) contains a value other than x_f (features_to_vary of the P4 taxonomy with a non-empty grid).
- Per-patient movability null of O-A2: exact enumeration per patient, Monte Carlo across patients.
"""
from __future__ import annotations

import csv
import itertools
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np

OUT = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/q1_domain_ckd")
ROLE_TABLE = OUT / "a0_role_table" / "ckd_role_table.csv"
LOCK_SET = OUT / "a0_role_table" / "ckd_lock_set.txt"
AGREEMENT = OUT / "a1_extraction" / "agreement" / "agreement_kdigo.json"
PASSAGES = {
    "e1": OUT / "a1_extraction" / "agreement" / "kdigo_passages_extractor1_claude_v1.csv",
    "e2": OUT / "a1_extraction" / "agreement" / "kdigo_passages_extractor2_claude_fallback_v2.csv",
}
ANALYTIC = OUT / "a0_nhanes_ckd" / "nhanes_ckd_analytic_2017-2023.csv"
ANALYTIC_SHA256 = "199bd7f2c72931552b2daa0cd2840ff2567b103435323e9d5d5fee18806f820f"
ROLE_TABLE_SHA256 = "cccea5af3c7c4a5a14c0ceb500d5e23432a95db5e3f8b692b500bcdc9698194e"
LOCK_SET_SHA256 = "78c013db95236bd3b4185189ada14c6303050a2f9d608377ec2ec9d431ea0095"

# MentHlth in NHANES = PHQ-9 total in P7 bands (nhanes-diabetes recode_phq9_to_menthlth): 0-4 -> 0, 5-9 -> 5,
# 10-14 -> 10, 15-19 -> 20, 20-27 -> 30. A value between band codes (possible after DiCE) is assigned the band of
# the largest code not above it.
PHQ_BAND_CODES = (0, 5, 10, 20, 30)


def load_roles() -> Tuple[List[str], Dict[str, str], Dict[str, str]]:
    feats, role, direction = [], {}, {}
    with open(ROLE_TABLE, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            feats.append(r["variable"])
            role[r["variable"]] = r["role"]
            direction[r["variable"]] = r["direction"]
    return feats, role, direction


def load_lock_set() -> List[str]:
    return [l.strip() for l in LOCK_SET.read_text(encoding="utf-8").splitlines() if l.strip()]


FEATURES, ROLE, DIRECTION = load_roles()
LOCK = load_lock_set()
INDICATORS = {f for f, r in ROLE.items() if r == "indicator"}
LEVERS = {f for f, r in ROLE.items() if r == "lever"}
TREATABLE = {f for f, r in ROLE.items() if r == "treatable"}


# ----------------------------------------------------------------------------------------------- edges
def kdigo_edges() -> List[dict]:
    """Agreed KDIGO edges at NHANES item level, with strength (C8: weaker of the two), grade and population."""
    ag = json.loads(AGREEMENT.read_text(encoding="utf-8"))
    pops: Dict[Tuple[str, str], Set[str]] = {}
    grades: Dict[Tuple[str, str], Set[str]] = {}
    for p in PASSAGES.values():
        with open(p, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("quotation_ok", "True") not in ("True", "true", "1"):
                    continue
                k = (r["source"], r["target"])
                pops.setdefault(k, set()).add(r["population"].strip())
                if r.get("grade", "").strip():
                    grades.setdefault(k, set()).add(r["grade"].strip())
    out = []
    for e in ag["agreed_graph_intersection"]:
        k = (e["source"], e["target"])
        for item in e["nhanes_items"]:
            s, t = item.split("->")
            out.append({"src": s, "dst": t, "authority": "KDIGO", "strength": e["strength_agreed_weaker"],
                        "grade": ";".join(sorted(grades.get(k, set()))), "graded": bool(grades.get(k)),
                        "population": sorted(pops.get(k, set())),
                        "scope_ckd_only": all("CKD" in x for x in pops.get(k, {"?"}))})
    return out


def ada_edges() -> List[dict]:
    """ADA 2026 edges of P7 (depgraph.edges) whose both ends are CKD items; duplicates collapsed per (src, dst)."""
    from depgraph.edges import EDGES  # noqa: WPS433 (P7 repo on sys.path)
    seen: Dict[Tuple[str, str], dict] = {}
    for e in EDGES:
        if e.src in ROLE and e.dst in ROLE:
            k = (e.src, e.dst)
            g = e.grade in ("A", "B", "C", "E")
            if k not in seen:
                seen[k] = {"src": e.src, "dst": e.dst, "authority": "ADA", "strength": "graded" if g else "narrative",
                           "grade": e.grade, "graded": g, "population": ["people with or at risk of diabetes"],
                           "scope_ckd_only": False}
            elif g and not seen[k]["graded"]:
                seen[k].update(strength="graded", grade=e.grade, graded=True)
    return list(seen.values())


def edge_set(edges: Iterable[dict], *, graded_only: bool = False, in_scope_ckd: Optional[bool] = None) -> Set[Tuple[str, str]]:
    """(src, dst) pairs passing the strength filter and, for the in-scope reading, the population filter.
    in_scope_ckd = None: ignore population; True/False: the patient's CKD label (edge scoped to CKD applies only
    when the patient has the label)."""
    out = set()
    for e in edges:
        if graded_only and not e["graded"]:
            continue
        if in_scope_ckd is not None and e["scope_ckd_only"] and not in_scope_ckd:
            continue
        out.add((e["src"], e["dst"]))
    return out


# ---------------------------------------------------------------------------------- path constraint
def supported(v: str, S: Set[str], E: Set[Tuple[str, str]], k: int = 1, strict: bool = False,
              role: Dict[str, str] = ROLE) -> bool:
    """Is indicator v in S supported by a lever in S through a path of at most k edges in E whose intermediate
    nodes are treatable (and in S when strict)?"""
    preds: Dict[str, Set[str]] = {}
    for a, b in E:
        preds.setdefault(b, set()).add(a)
    frontier = {v}
    for _ in range(k):
        nxt = set()
        for w in frontier:
            for u in preds.get(w, ()):
                if role.get(u) == "lever" and u in S:
                    return True
                if role.get(u) == "treatable" and (u in S or not strict):
                    nxt.add(u)
        frontier = nxt
        if not frontier:
            break
    return False


def classify(changed: Iterable[str], E: Set[Tuple[str, str]], k: int = 1, strict: bool = False,
             role: Dict[str, str] = ROLE) -> dict:
    S = set(changed)
    inds = sorted(f for f in S if role.get(f) == "indicator")
    unsup = [v for v in inds if not supported(v, S, E, k, strict, role)]
    has_lever = any(role.get(f) == "lever" for f in S)
    has_treat = any(role.get(f) == "treatable" for f in S)
    return {"touches": bool(inds), "leaks": bool(unsup), "unsupported": unsup,
            "n_indicator_changes": len(inds), "n_changes": len(S),
            "fully_unactionable": bool(inds) and not has_lever and not has_treat}


def accept(changed: Iterable[str], E: Set[Tuple[str, str]], k: int = 1, strict: bool = False) -> bool:
    return not classify(changed, E, k, strict)["leaks"]


def supporting_levers(v: str, S: Set[str], E: Set[Tuple[str, str]]) -> List[str]:
    """Levers u in S with a direct (k = 1) edge into v."""
    return sorted(u for (u, w) in E if w == v and u in S and ROLE.get(u) == "lever")


# --------------------------------------------------------------------------------------- change sizes
def phq_band(x: float) -> int:
    return max(i for i, c in enumerate(PHQ_BAND_CODES) if c <= round(x) + 1e-9) if round(x) >= 0 else 0


def indicator_step(f: str, before: float, after: float) -> int:
    """Change size of an indicator in its own steps: GenHlth levels, MentHlth PHQ-9 bands (absolute value)."""
    if f == "GenHlth":
        return abs(int(round(after)) - int(round(before)))
    if f == "MentHlth":
        return abs(phq_band(after) - phq_band(before))
    raise ValueError(f)


def capped_ok(S: Set[str], before: Dict[str, float], after: Dict[str, float], E: Set[Tuple[str, str]]) -> bool:
    """Capped reading (prereg 4.7): route-aware acceptance (k = 1) and every supported indicator moves at most one
    GenHlth level / one PHQ-9 band per supporting lever in S."""
    if not accept(S, E, 1, False):
        return False
    for v in S:
        if ROLE.get(v) != "indicator":
            continue
        n_lev = len(supporting_levers(v, S, E))
        if indicator_step(v, before[v], after[v]) > n_lev:
            return False
    return True


# ------------------------------------------------------------------------------- movability null (O-A2)
def oshare(counts: Dict[str, int], labelled: Iterable[str]) -> float:
    tot = sum(counts.values())
    return 0.0 if tot == 0 else sum(counts.get(f, 0) for f in labelled) / tot


def patient_null(counts: Dict[str, int], movable: Sequence[str], n_ind: int) -> np.ndarray:
    """All values of the patient's O-share when the n_ind indicator labels fall on a uniformly random subset of
    size n_ind of the movable set (exact enumeration; each subset equally likely)."""
    if n_ind == 0:
        return np.zeros(1)
    return np.array([oshare(counts, sub) for sub in itertools.combinations(sorted(movable), n_ind)])


def movability_null_p(observed: Sequence[float], nulls: Sequence[np.ndarray], draws: int = 100_000,
                      seed: int = 20261111, chunk: int = 10_000) -> Tuple[float, float, int]:
    """T = mean observed O-share; T* = mean of one uniformly drawn subset value per patient; p = (1 + #{T* >= T})
    / (draws + 1). Ties count as >= (tolerance 1e-12). Returns (T, p, n_ge)."""
    T = float(np.mean(observed))
    rng = np.random.default_rng(seed)
    n = len(nulls)
    n_ge, done = 0, 0
    while done < draws:
        b = min(chunk, draws - done)
        tot = np.zeros(b)
        for j in range(n):
            vals = nulls[j]
            tot += vals[rng.integers(0, len(vals), size=b)]
        n_ge += int(np.sum(tot / n >= T - 1e-12))
        done += b
    return T, (1 + n_ge) / (draws + 1), n_ge


# --------------------------------------------------------------------------------------- statistics
def clopper_pearson(x: int, n: int, level: float) -> Tuple[float, float]:
    from scipy.stats import beta
    a = 1 - level
    lo = 0.0 if x == 0 else float(beta.ppf(a / 2, x, n - x + 1))
    hi = 1.0 if x == n else float(beta.ppf(1 - a / 2, x + 1, n - x))
    return lo, hi


def boot_means(x: np.ndarray, B: int = 2000, seed: int = 20261111) -> np.ndarray:
    """Percentile-bootstrap distribution of the mean over patients (2,000 resamples, seed 20261111)."""
    rng = np.random.default_rng(seed)
    n = len(x)
    return np.array([np.mean(x[rng.integers(0, n, n)]) for _ in range(B)])


def trunc(x, nd: int = 4) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "NA"
    f = 10 ** nd
    return f"{math.trunc(x * f) / f:.{nd}f}"
