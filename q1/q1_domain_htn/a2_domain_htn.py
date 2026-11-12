"""P7 Q1 step A2-HTN: domain objects shared by the HTN run and analysis scripts (addendum HTN v3).

Same logic as the frozen CKD a2_domain.py (path constraint, movability null, statistics are imported from it
unchanged); only the domain inputs differ:
- roles, directions, lock set: the frozen A0-HTN role table (hash-checked);
- AHA/ACC edges: the HTN agreed (intersection) graph of step A1-HTN mapped to NHANES HTN items; edges with
  BLOOD_PRESSURE at either end have no item and drop out (addendum 5.3, rule R-OUT);
- KDIGO edges (secondary authority, addendum 2.3): the frozen CKD agreed graph re-mapped to HTN items;
- ADA edges: depgraph.edges restricted to HTN items;
- in-scope reading: an AHA/ACC edge whose stated populations all name hypertension or high blood pressure applies
  only to cohort patients with L1 = 1.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "q1_domain_ckd"))
import a2_domain as CKD  # noqa: E402  (frozen CKD domain helpers; functions take roles/edges as arguments)

OUT = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/q1_domain_htn")
ROLE_TABLE = OUT / "a0_role_table" / "htn_role_table.csv"
LOCK_SET = OUT / "a0_role_table" / "htn_lock_set.txt"
ANALYTIC = OUT / "a0_nhanes_htn" / "nhanes_htn_analytic_2017-2023.csv"
ANALYTIC_SHA256 = "e8efa0d31b64f046b08f4c104330a507442dbd53afd72023960df12244642718"
ROLE_TABLE_SHA256 = "f1a6b6d174ee5e533b4c5d83d11ad525d21aa27ca8fc08adc48f6cf876a94302"
LOCK_SET_SHA256 = "78c013db95236bd3b4185189ada14c6303050a2f9d608377ec2ec9d431ea0095"
AGREEMENT = OUT / "a1_extraction" / "agreement" / "agreement_aha.json"
PASSAGES = {"A": OUT / "a1_extraction" / "agreement" / "aha_passages_extractorA_claude_v1.csv",
            "B": OUT / "a1_extraction" / "agreement" / "aha_passages_extractorB_qwen72b_v2.csv"}
CKD_AGREEMENT = CKD.OUT / "a1_extraction" / "agreement" / "agreement_kdigo.json"
ITEM_MAP = json.loads((HERE / "concepts_constructs_htn_v1.json").read_text(encoding="utf-8"))["concept_to_item"]["nhanes_htn"]
HTN_WORDS = ("hypertension", "high blood pressure", "elevated blood pressure", "elevated bp", "high bp")


def load_roles():
    feats, role, direction = [], {}, {}
    with open(ROLE_TABLE, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            feats.append(r["variable"])
            role[r["variable"]] = r["role"]
            direction[r["variable"]] = r["direction"]
    return feats, role, direction


FEATURES, ROLE, DIRECTION = load_roles()
LOCK = [l.strip() for l in LOCK_SET.read_text(encoding="utf-8").splitlines() if l.strip()]
INDICATORS = {f for f, r in ROLE.items() if r == "indicator"}
LEVERS = {f for f, r in ROLE.items() if r == "lever"}


def _items(u, v):
    return [(a, b) for a in ITEM_MAP.get(u, []) for b in ITEM_MAP.get(v, []) if a != b]


def aha_edges() -> List[dict]:
    if not AGREEMENT.exists():
        return []
    ag = json.loads(AGREEMENT.read_text(encoding="utf-8"))
    pops: Dict[Tuple[str, str], Set[str]] = {}
    grades: Dict[Tuple[str, str], Set[str]] = {}
    for p in PASSAGES.values():
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("quotation_ok") not in ("True", "true", "1"):
                    continue
                k = (r["source"], r["target"])
                pops.setdefault(k, set()).add(r["population"].strip())
                if r.get("grade", "").strip():
                    grades.setdefault(k, set()).add(r["grade"].strip())
    out = []
    for e in ag["agreed_graph_intersection"]:
        k = (e["source"], e["target"])
        P = pops.get(k, {"?"})
        for s, t in _items(*k):
            out.append({"src": s, "dst": t, "authority": "AHA/ACC", "strength": e["strength_agreed_weaker"],
                        "grade": ";".join(sorted(grades.get(k, set()))), "graded": bool(grades.get(k)),
                        "population": sorted(P),
                        "scope_htn_only": all(any(w in x.lower() for w in HTN_WORDS) for x in P)})
    return out


def kdigo_edges() -> List[dict]:
    ag = json.loads(CKD_AGREEMENT.read_text(encoding="utf-8"))
    out = []
    for e in ag["agreed_graph_intersection"]:
        for s, t in _items(e["source"], e["target"]):
            out.append({"src": s, "dst": t, "authority": "KDIGO", "strength": e["strength_agreed_weaker"], "grade": "",
                        "graded": False, "population": [], "scope_htn_only": False})
    return out


def ada_edges() -> List[dict]:
    from depgraph.edges import EDGES  # noqa: WPS433
    seen: Dict[Tuple[str, str], dict] = {}
    for e in EDGES:
        if e.src in ROLE and e.dst in ROLE:
            k = (e.src, e.dst)
            g = e.grade in ("A", "B", "C", "E")
            if k not in seen:
                seen[k] = {"src": e.src, "dst": e.dst, "authority": "ADA", "strength": "graded" if g else "narrative",
                           "grade": e.grade, "graded": g, "population": ["people with or at risk of diabetes"],
                           "scope_htn_only": False}
            elif g and not seen[k]["graded"]:
                seen[k].update(strength="graded", grade=e.grade, graded=True)
    return list(seen.values())


def edge_set(edges: Iterable[dict], *, graded_only: bool = False, in_scope_htn: Optional[bool] = None):
    out = set()
    for e in edges:
        if graded_only and not e["graded"]:
            continue
        if in_scope_htn is not None and e["scope_htn_only"] and not in_scope_htn:
            continue
        out.add((e["src"], e["dst"]))
    return out


def classify(changed, E, k=1, strict=False, role=None):
    return CKD.classify(changed, E, k, strict, role or ROLE)


def accept(changed, E, k=1, strict=False, role=None):
    return not classify(changed, E, k, strict, role)["leaks"]


def supporting_levers(v, S, E):
    return sorted(u for (u, w) in E if w == v and u in S and ROLE.get(u) == "lever")


def capped_ok(S, before, after, E):
    if not accept(S, E, 1, False):
        return False
    for v in S:
        if ROLE.get(v) != "indicator":
            continue
        if CKD.indicator_step(v, before[v], after[v]) > len(supporting_levers(v, S, E)):
            return False
    return True


indicator_step = CKD.indicator_step
oshare, patient_null, movability_null_p = CKD.oshare, CKD.patient_null, CKD.movability_null_p
clopper_pearson, boot_means, trunc = CKD.clopper_pearson, CKD.boot_means, CKD.trunc
