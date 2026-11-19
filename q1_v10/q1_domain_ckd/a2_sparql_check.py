"""P7 Q1 step A2: Python vs SPARQL check of the path constraint (prereg v3 3 "Software check", 5.6 "Path constraint").

Writes the CKD domain graph (CKD role assignments of the NHANES items, KDIGO agreed Statements and ADA Statements,
reified with authority and scope) as Turtle, loads it with rdflib, and evaluates leakage with SPARQL ASK queries.
  --test          10,000 random change sets per reading; Python (a2_domain.classify) and SPARQL must agree on all.
  --audit COHORT  every audited counterfactual of a2_runs_<COHORT> (all generators and modes), primary reading
                  (KDIGO, k = 1) and ADA k = 1; must agree on 100%.
rdflib is not in the P4 or p7-carla312 venv; this script runs in the base Anaconda Python (rdflib 7.6.0), with -I.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")

import rdflib  # noqa: E402

import a2_domain as D  # noqa: E402

KG = "https://github.com/thieuanhvan/diabetes-xai-dependencygraph/kg#"


def turtle() -> str:
    lines = [f"@prefix kg: <{KG}> .", "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .", ""]
    for f in D.FEATURES:
        lines.append(f"kg:ra_{f}_CKD a kg:RoleAssignment ; kg:ofVariable kg:{f} ; kg:assignedIn kg:CKD ; kg:role kg:{D.ROLE[f]} .")
    for j, e in enumerate(D.kdigo_edges() + D.ada_edges()):
        lines.append(f"kg:st{j} a kg:Statement ; kg:subject kg:{e['src']} ; kg:object kg:{e['dst']} ; "
                     f"kg:authority kg:{e['authority']} ; kg:graded {'true' if e['graded'] else 'false'} ; "
                     f"kg:scopeCKDOnly {'true' if e['scope_ckd_only'] else 'false'} .")
    return "\n".join(lines) + "\n"


def role_pat(var, role):
    return f"?ra_{var[1:]} kg:ofVariable {var} ; kg:assignedIn kg:CKD ; kg:role kg:{role} ."


def st_pat(s, o, auths):
    vals = " ".join(f"kg:{x}" for x in auths)
    return f"[] a kg:Statement ; kg:subject {s} ; kg:object {o} ; kg:authority ?au_{s[1:]}{o[1:]} . VALUES ?au_{s[1:]}{o[1:]} {{ {vals} }}"


def ask_leaks(g, S, auths, k=1, strict=False) -> bool:
    """SPARQL: some indicator v in S has no lever u in S with a path of <= k Statements (intermediate treatable)."""
    if not S:
        return False
    vs = " ".join(f"kg:{f}" for f in sorted(S))
    paths = [f"{{ ?u kg:inS true . {role_pat('?u', 'lever')} {st_pat('?u', '?v', auths)} }}"]
    if k >= 2:
        ins = "?t kg:inS true ." if strict else ""
        paths.append(f"{{ ?u kg:inS true . {role_pat('?u', 'lever')} {role_pat('?t', 'treatable')} {ins} "
                     f"{st_pat('?u', '?t', auths)} {st_pat('?t', '?v', auths)} }}")
    q = (f"PREFIX kg: <{KG}> ASK {{ VALUES ?v {{ {vs} }} {role_pat('?v', 'indicator')} "
         f"FILTER NOT EXISTS {{ {' UNION '.join(paths)} }} }}")
    # membership of S is asserted as temporary triples
    for f in S:
        g.add((rdflib.URIRef(KG + f), rdflib.URIRef(KG + "inS"), rdflib.Literal(True)))
    try:
        return bool(g.query(q).askAnswer)
    finally:
        for f in S:
            g.remove((rdflib.URIRef(KG + f), rdflib.URIRef(KG + "inS"), rdflib.Literal(True)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--audit", default="")
    ap.add_argument("--n", type=int, default=10_000)
    a = ap.parse_args()
    ttl = turtle()
    outd = D.OUT / "a2_analysis"
    outd.mkdir(parents=True, exist_ok=True)
    (outd / "ckd_domain_graph.ttl").write_text(ttl, encoding="utf-8", newline="\n")
    g = rdflib.Graph()
    g.parse(data=ttl, format="turtle")
    E_K, E_A = D.edge_set(D.kdigo_edges()), D.edge_set(D.ada_edges())
    readings = {"kdigo_k1": (["KDIGO"], E_K, 1, False), "ada_k1": (["ADA"], E_A, 1, False),
                "union_k1": (["KDIGO", "ADA"], E_K | E_A, 1, False),
                "union_k2_permissive": (["KDIGO", "ADA"], E_K | E_A, 2, False),
                "union_k2_strict": (["KDIGO", "ADA"], E_K | E_A, 2, True)}
    res = {"rdflib": rdflib.__version__}
    if a.test:
        rng = random.Random(20261111)
        mov = [f for f in D.FEATURES if D.ROLE[f] != "immutable"] + ["Education", "Income", "AnyHealthcare"]
        for name, (au, E, k, strict) in readings.items():
            dis, nleak, memo = 0, 0, {}
            for _ in range(a.n):
                S = set(rng.sample(mov, rng.randint(1, 5)))
                py = D.classify(S, E, k, strict)["leaks"]
                key = frozenset(S)  # SPARQL is deterministic: each distinct set is queried once
                if key not in memo:
                    memo[key] = ask_leaks(g, S, au, k, strict)
                sp = memo[key]
                dis += py != sp
                nleak += py
            res[f"test_{name}"] = {"n_sets": a.n, "n_distinct_sets_queried": len(memo), "disagreements": dis, "python_leaking": nleak}
            print(name, res[f"test_{name}"], flush=True)
        (outd / "sparql_unit_test.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    if a.audit:
        import csv
        R = D.OUT / f"a2_runs_{a.audit}"
        sets_ = []
        for p in sorted(R.glob("dice_*_seed*.csv")) + [R / "exhaustive.csv"]:
            if p.name.endswith("_status.csv"):
                continue
            with open(p, encoding="utf-8") as fh:
                sets_ += [frozenset(x for x in r["changed"].split(";") if x) for r in csv.DictReader(fh)]
        uniq = sorted(set(sets_), key=sorted)
        for name in ("kdigo_k1", "ada_k1"):
            au, E, k, strict = readings[name]
            dis = [sorted(S) for S in uniq if D.classify(S, E, k, strict)["leaks"] != ask_leaks(g, S, au, k, strict)]
            res[f"audit_{name}"] = {"n_cf": len(sets_), "n_distinct_change_sets": len(uniq), "disagreements": len(dis),
                                    "examples": dis[:5]}
            print(name, res[f"audit_{name}"], flush=True)
        (outd / f"sparql_audit_{a.audit}.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
