"""Step A1 agreement (prereg v3 4.4, 4.8): quotation check on both KDIGO extractors, agreement, agreed edge set.

Extractor 1 = Claude, frozen prompt v1 (a1_extractor1_claude/, deviation D2).
Extractor 2 = fallback second Claude instance, prompt v2 (a1_extraction/extractor2_claude_fallback/, event E1),
because the Qwen recall gate failed; Qwen KDIGO outputs are not used.

Reuses the frozen parsing rule and quotation check of a1_ingest_kaggle_zip.py (parse_chunk, quotation_ok).
Unit (clarification C7): the 88 candidate Concept pairs (u, v), u != v, u in the 8 lever/treatable Concepts, v in
all 12 Concepts; a pair is present for an extractor if at least one passage of it passes the quotation check.
Secondary reading on the NHANES CKD items (30 pairs) after the frozen Concept-to-item map.
Graph = intersection; union reported as secondary. Degenerate = no agreed edge into GenHlth or MentHlth.
Usage: python -I a1_agreement.py
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime

from q1_common import FREEZE, OUT, check_prereg, sha256_file, trunc, write_json
from a1_ingest_kaggle_zip import STRENGTH_ORDER, TEXT, parse_chunk, write_rows

EXTRACTORS = {"extractor1_claude_v1": OUT / "a1_extractor1_claude",
              "extractor2_claude_fallback_v2": OUT / "a1_extraction" / "extractor2_claude_fallback"}
DEST = OUT / "a1_extraction" / "agreement"


def verify_hashes(folder):
    for line in (folder / "outputs_sha256.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            h, name = line.split(None, 1)
            assert sha256_file(folder / name.lstrip("*")) == h, f"hash mismatch {folder / name}"


def agreement(A: set, B: set, universe: list) -> dict:
    a = sum(1 for p in universe if p in A and p in B)
    b = sum(1 for p in universe if p in A and p not in B)
    c = sum(1 for p in universe if p not in A and p in B)
    d = len(universe) - a - b - c
    n = len(universe)
    po = (a + d) / n
    pe = ((a + b) * (a + c) + (c + d) * (b + d)) / n ** 2
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    ppos = 2 * a / (2 * a + b + c) if (2 * a + b + c) else float("nan")
    pneg = 2 * d / (2 * d + b + c) if (2 * d + b + c) else float("nan")
    return {"n_pairs": n, "both": a, "only_e1": b, "only_e2": c, "neither": d,
            "observed_agreement": trunc(po), "cohen_kappa": trunc(kappa), "pabak": trunc(2 * po - 1),
            "positive_agreement": trunc(ppos), "negative_agreement": trunc(pneg)}


def main():
    check_prereg()
    sett = json.loads((FREEZE / "design" / "extraction_settings_v1.json").read_text(encoding="utf-8"))
    voc = json.loads((FREEZE / "design" / "concepts_constructs_v1.json").read_text(encoding="utf-8"))
    props = sett["json_schema_v1"]["properties"]["edges"]["items"]["properties"]
    src_ok, dst_ok = props["source"]["enum"], props["target"]["enum"]
    index = [r for r in csv.DictReader(open(FREEZE / "chunk_index.csv", encoding="utf-8")) if r["document"] == "kdigo"]
    p = TEXT["kdigo"]
    pages = {"kdigo": ((p.parent / (p.name + "_raw.txt")).read_text(encoding="utf-8").split("\f"),
                       (p.parent / (p.name + "_layout.txt")).read_text(encoding="utf-8").split("\f"))}
    universe = [(u, v) for u in src_ok for v in dst_ok if u != v]
    item = voc["concept_to_item"]["nhanes_ckd"]
    item_src = sorted({i for c in src_ok for i in item[c]})
    item_dst = sorted({i for c in dst_ok for i in item[c]})
    item_universe = [(a, b) for a in item_src for b in item_dst if a != b]

    DEST.mkdir(parents=True, exist_ok=True)
    per, stats_all, before, after = {}, {}, {}, {}
    for name, folder in EXTRACTORS.items():
        verify_hashes(folder)
        stats = defaultdict(lambda: defaultdict(int))
        rows = []
        for r in index:
            files = {f"raw/{r['chunk_id']}.txt": (folder / f"{r['chunk_id']}.json").read_bytes()}
            rows += parse_chunk(r["chunk_id"], "kdigo", files, pages, set(src_ok), set(dst_ok), voc, stats)
        write_rows(DEST / f"kdigo_passages_{name}.csv", rows)
        per[name] = rows
        st = dict(stats["kdigo"])
        st["passages_after_quote_check"] = sum(r["quotation_ok"] for r in rows)
        stats_all[name] = st
        before[name] = {(r["source"], r["target"]) for r in rows}
        pairs = {}
        for r in rows:
            if not r["quotation_ok"]:
                continue
            k = (r["source"], r["target"])
            if k not in pairs or STRENGTH_ORDER.get(r["strength"], 0) > STRENGTH_ORDER.get(pairs[k]["strength"], 0):
                pairs[k] = dict(r)
        after[name] = pairs
        write_rows(DEST / f"kdigo_pairs_{name}.csv", list(pairs.values()))

    e1, e2 = EXTRACTORS
    A, B = set(after[e1]), set(after[e2])

    def to_items(S):
        return {(a, b) for (u, v) in S for a in item[u] for b in item[v] if a != b}

    inter = sorted(A & B)
    agreed = []
    for k in inter:
        s1, s2 = after[e1][k]["strength"], after[e2][k]["strength"]
        weaker = s1 if STRENGTH_ORDER[s1] <= STRENGTH_ORDER[s2] else s2
        agreed.append({"source": k[0], "target": k[1], "nhanes_items": sorted(f"{a}->{b}" for a in item[k[0]]
                                                                              for b in item[k[1]] if a != b),
                       "strength_e1": s1, "strength_e2": s2, "strength_agreed_weaker": weaker,
                       "page_e1": after[e1][k]["page"], "page_e2": after[e2][k]["page"],
                       "section_e1": after[e1][k]["section"], "section_e2": after[e2][k]["section"]})
    agreed_items = to_items(A & B)
    into_ind = sorted(f"{a}->{b}" for a, b in agreed_items if b in ("GenHlth", "MentHlth"))
    union_into_ind = sorted(f"{a}->{b}" for a, b in to_items(A | B) if b in ("GenHlth", "MentHlth"))
    res = {
        "_about": "P7 Q1 step A1, KDIGO agreement (prereg v3 4.4, 4.8). Extractor 2 = fallback Claude instance "
                  "(event E1). Quotation check and parsing as frozen; unit and strength rule as clarifications C7, C8.",
        "written": f"{datetime.now():%d/%m/%Y %H:%M}",
        "input_hashes": {n: sha256_file(f / "outputs_sha256.txt") for n, f in EXTRACTORS.items()},
        "parse_and_drop_counts": stats_all,
        "pairs_before_quote_check": {n: len(v) for n, v in before.items()},
        "pairs_after_quote_check": {n: len(v) for n, v in after.items()},
        "agreement_concept_pairs_primary": agreement(A, B, universe),
        "agreement_concept_pairs_before_quote_check": agreement(before[e1], before[e2], universe),
        "agreement_nhanes_items_secondary": agreement(to_items(A), to_items(B), item_universe),
        "pairs_only_e1": sorted(map(list, A - B)), "pairs_only_e2": sorted(map(list, B - A)),
        "agreed_graph_intersection": agreed,
        "union_pairs_secondary": sorted(map(list, A | B)),
        "reading_rules_A1": {
            "agreed_nhanes_edges_into_GenHlth_or_MentHlth": into_ind,
            "degenerate": len(into_ind) == 0,
            "near_degenerate": "not evaluable at A1: needs the cohort's per-patient movability of each supporting "
                               "lever (prereg 4.8), available only after the CKD model is fitted",
            "supporting_levers_for_later_near_degenerate_check": sorted({e.split("->")[0] for e in into_ind}),
            "union_nhanes_edges_into_GenHlth_or_MentHlth_secondary": union_into_ind},
    }
    write_json(DEST / "agreement_kdigo.json", res)
    print(json.dumps({k: res[k] for k in ("parse_and_drop_counts", "pairs_before_quote_check", "pairs_after_quote_check",
                                          "agreement_concept_pairs_primary", "agreement_concept_pairs_before_quote_check",
                                          "agreement_nhanes_items_secondary", "pairs_only_e1", "pairs_only_e2",
                                          "agreed_graph_intersection", "reading_rules_A1")}, indent=1))
    names = sorted(x.name for x in DEST.iterdir() if x.name != "outputs_sha256.txt")
    (DEST / "outputs_sha256.txt").write_text("".join(f"{sha256_file(DEST / n)} *{n}\n" for n in names), encoding="utf-8")


if __name__ == "__main__":
    main()
