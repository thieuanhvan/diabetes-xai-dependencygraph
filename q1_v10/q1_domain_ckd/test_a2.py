"""Unit tests for step A2 (prereg v3 5.6, the tests that concern extension A); must pass before the real-data runs.

Run (P4 venv): python -I test_a2.py      (plain asserts; prints one line per test; exit 1 on any failure)
The Python-SPARQL agreement test (10,000 random change sets) is a2_sparql_check.py --test (Anaconda, rdflib).
"""
from __future__ import annotations

import itertools
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import a2_domain as D  # noqa: E402

FAILED = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name, flush=True)
    if not cond:
        FAILED.append(name)


def test_null_exact_vs_bruteforce():
    rng = np.random.default_rng(1)
    for _ in range(50):
        m = int(rng.integers(2, 8))
        M = [f"f{j}" for j in range(m)]
        n_ind = int(rng.integers(1, min(3, m) + 1))
        cnt = {f: int(rng.integers(0, 6)) for f in M}
        ex = sorted(np.round(D.patient_null(cnt, M, n_ind), 12))
        # brute force: every permutation of labels (n_ind indicators, m - n_ind others), equally likely
        bf = Counter()
        for perm in itertools.permutations(range(m)):
            lab = [M[i] for i in perm[:n_ind]]
            bf[round(D.oshare(cnt, lab), 12)] += 1
        tot = sum(bf.values())
        exc = Counter(ex)
        ok = all(abs(exc[v] / len(ex) - bf[v] / tot) < 1e-12 for v in set(bf) | set(exc))
        if not ok:
            return check("movability null: exact per-patient enumeration = brute force over permutations", False)
    check("movability null: exact per-patient enumeration = brute force over permutations", True)


def test_mc_vs_exact_tail():
    rng = np.random.default_rng(2)
    nulls, obs = [], []
    for _ in range(4):
        M = [f"f{j}" for j in range(5)]
        cnt = {f: int(rng.integers(0, 5)) for f in M}
        nulls.append(D.patient_null(cnt, M, 2))
        obs.append(float(nulls[-1].max()))
    T = float(np.mean(obs))
    exact = np.mean([np.mean(c) >= T - 1e-12 for c in itertools.product(*nulls)])
    _, p, _ = D.movability_null_p(obs, nulls, draws=100_000, seed=20261111)
    se = math.sqrt(max(exact * (1 - exact), 1e-6) / 100_000)
    check(f"movability null: MC p ({p:.5f}) matches exact tail ({exact:.5f}) within 4 SE", abs(p - exact) < 4 * se + 1e-5)


def test_null_uniform():
    """p is uniform under a generator that changes movable features uniformly at random (1,000 cohorts, KS p > 0.01).
    Monte Carlo draws per cohort reduced to 2,000 for run time (the null is the same; only its resolution changes)."""
    from scipy.stats import kstest
    rng = np.random.default_rng(3)
    ps = []
    for c in range(1000):
        obs, nulls = [], []
        for _ in range(40):
            m = int(rng.integers(3, 11))
            M = [f"f{j}" for j in range(m)]
            n_ind = int(rng.integers(0, 3))
            ind = set(rng.choice(M, n_ind, replace=False)) if n_ind else set()
            cnt = Counter()
            for _ in range(int(rng.integers(3, 26))):
                k = int(rng.integers(1, min(3, m) + 1))
                cnt.update(rng.choice(M, k, replace=False).tolist())
            obs.append(D.oshare(cnt, ind))
            nulls.append(D.patient_null(cnt, M, n_ind))
        _, p, _ = D.movability_null_p(obs, nulls, draws=2000, seed=c)
        ps.append(p)
    ks = kstest(ps, "uniform").pvalue
    check(f"movability null: p uniform under a uniform generator (KS p = {ks:.4f} > 0.01)", ks > 0.01)


def test_path_constraint():
    E = {("BMI", "GenHlth"), ("PhysActivity", "MentHlth"), ("BMI", "HighBP"), ("HighBP", "MentHlth")}
    c = D.classify
    check("path: indicator-only change leaks, fully unactionable", c({"GenHlth"}, E)["leaks"] and c({"GenHlth"}, E)["fully_unactionable"])
    check("path: BMI supports GenHlth at k = 1", not c({"BMI", "GenHlth"}, E)["leaks"])
    check("path: BMI does not support MentHlth at k = 1", c({"BMI", "MentHlth"}, E)["leaks"])
    check("path: BMI -> HighBP -> MentHlth supports at k = 2 permissive", not c({"BMI", "MentHlth"}, E, 2, False)["leaks"])
    check("path: k = 2 strict needs HighBP in S", c({"BMI", "MentHlth"}, E, 2, True)["leaks"]
          and not c({"BMI", "HighBP", "MentHlth"}, E, 2, True)["leaks"])
    check("path: treatable alone is not a supporting source", c({"HighBP", "MentHlth"}, E, 2, False)["leaks"]
          and not c({"HighBP", "MentHlth"}, E)["fully_unactionable"])
    # agreement with P7's universal-reading admissible() on ADA edges (k = 1), random sets
    sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
    from depgraph import audit as A
    EA = D.edge_set(D.ada_edges())
    rng = np.random.default_rng(4)
    mov = ["HighBP", "HighChol", "BMI", "Smoker", "PhysActivity", "GenHlth", "MentHlth", "Education", "Income", "AnyHealthcare"]
    dis = sum(D.classify(S, EA)["leaks"] != A.classify(S, reading="narrow", rule="edge")["unsupported"]
              for S in (set(rng.choice(mov, int(rng.integers(1, 5)), replace=False)) for _ in range(5000)))
    check(f"path: ADA k = 1 equals depgraph.audit edge rule on 5,000 random sets ({dis} disagreements)", dis == 0)


def test_bands_and_cap():
    check("PHQ band mapping 0,5,10,20,30 and in-between values",
          [D.phq_band(x) for x in (0, 4, 5, 9, 10, 17, 20, 29, 30)] == [0, 0, 1, 1, 2, 2, 3, 3, 4])
    E = {("BMI", "GenHlth"), ("PhysActivity", "MentHlth")}
    b = {"BMI": 30, "GenHlth": 4, "MentHlth": 30, "PhysActivity": 0}
    check("cap: one GenHlth level with BMI accepted", D.capped_ok({"BMI", "GenHlth"}, b, b | {"BMI": 28, "GenHlth": 3}, E))
    check("cap: two GenHlth levels with one lever rejected", not D.capped_ok({"BMI", "GenHlth"}, b, b | {"BMI": 28, "GenHlth": 2}, E))
    check("cap: MentHlth 30 -> 20 (one band) accepted", D.capped_ok({"PhysActivity", "MentHlth"}, b, b | {"PhysActivity": 1, "MentHlth": 20}, E))
    check("cap: MentHlth 30 -> 10 (two bands) rejected", not D.capped_ok({"PhysActivity", "MentHlth"}, b, b | {"PhysActivity": 1, "MentHlth": 10}, E))


def test_clopper_pearson():
    lo, hi = D.clopper_pearson(5, 20, 0.95)
    check(f"Clopper-Pearson 5/20 95% = (0.0866, 0.4910): ({lo:.4f}, {hi:.4f})", abs(lo - 0.0866) < 1e-4 and abs(hi - 0.4910) < 1e-4)
    check("Clopper-Pearson 20/20 upper = 1", D.clopper_pearson(20, 20, 0.99)[1] == 1.0)


def test_route_constraint_and_search_parity():
    """Synthetic patient whose only cheap flip is indicator-only: it leaks in published mode; the route-aware search
    returns a supported counterfactual or nothing. The value-returning search equals P7's search."""
    import a2_ckd_runs as RN
    RN.patch_taxonomy()
    E = D.edge_set(D.kdigo_edges())
    RN.P.admissible = lambda chg: D.accept(chg, E, 1, False)

    class Toy:  # class 0 iff GenHlth <= 2, or MentHlth <= 5 and Income >= 4
        def predict(self, X):
            g = X[:, D.FEATURES.index("GenHlth")]
            m = X[:, D.FEATURES.index("MentHlth")]
            inc = X[:, D.FEATURES.index("Income")]
            return np.where((g <= 2) | ((m <= 5) & (inc >= 4)), 0, 1)

    q = pd.Series({f: 0.0 for f in D.FEATURES})
    q.update({"BMI": 31, "GenHlth": 4, "MentHlth": 20, "PhysActivity": 0, "Smoker": 1, "HighBP": 1, "HighChol": 1,
              "Income": 2, "Education": 3, "AnyHealthcare": 1, "Age": 60, "Sex": 1, "Cycle": 0})
    pub = RN.search_full(Toy(), q, D.FEATURES)
    check("route toy: published best is indicator-only and leaks",
          pub[0][0] == ["GenHlth"] and D.classify(set(pub[0][0]), E)["leaks"])
    rt = RN.search_full(Toy(), q, D.FEATURES, set_ok=lambda S: D.accept(S, E, 1, False))
    check("route toy: route-aware output is empty or every CF supported",
          all(not D.classify(set(s), E)["leaks"] for s, *_ in rt))
    ok = True
    for mode in ("published", "route"):
        p7 = RN.EX.search(Toy(), q, D.FEATURES, "route_A" if mode == "route" else mode)
        mine = RN.search_full(Toy(), q, D.FEATURES, set_ok=(lambda S: D.accept(S, E, 1, False)) if mode == "route" else None)
        ok &= [(s, k, d) for s, k, d, _ in mine] == p7
    check("search parity: value-returning search = P7 search (published, route)", ok)


if __name__ == "__main__":
    test_null_exact_vs_bruteforce()
    test_mc_vs_exact_tail()
    test_path_constraint()
    test_bands_and_cap()
    test_clopper_pearson()
    test_route_constraint_and_search_parity()
    test_null_uniform()
    print("ALL PASS" if not FAILED else f"FAILED: {FAILED}")
    sys.exit(1 if FAILED else 0)
