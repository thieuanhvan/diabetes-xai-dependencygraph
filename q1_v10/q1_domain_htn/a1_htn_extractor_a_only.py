"""A1-HTN after the recall gate (addendum HTN v3, Sections 5.4, 5.5).

Extractor B (Qwen2.5-72B, prompt v2) failed the recall gate, so there is no fallback: the HTN agreed graph, H3-HTN and
A-Q4-HTN are "not reached". This script does only what the addendum allows in that case:
- parses extractor A's (Claude, prompt v1) five HTN chunk outputs with the frozen parsing rule and quotation check
  (against the frozen -raw / -layout text of the JACC PDF) and reports A's quotation-checked edges descriptively as a
  single-extractor graph (Concept pairs, the 70 audit-relevant and 88 candidate pairs, item-level mapping);
- reports A's same-prompt test-retest on the drawn chunk(s).
Extractor B's HTN outputs are hashed but not opened. Usage: python -I a1_htn_extractor_a_only.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from htn_common import CKD_FREEZE, CKD_TOOLS, FREEZE, OUT, REF_HTN, check_prereg, sha256_file, write_json  # noqa: E402

sys.path.insert(0, str(CKD_TOOLS))
from a1_ingest_kaggle_zip import STRENGTH_ORDER, parse_chunk, write_rows  # noqa: E402

A = OUT / "a1_extraction" / "extractorA_claude_v1"
B = OUT / "a1_extraction" / "extractorB_qwen72b_v2"
DEST = OUT / "a1_extraction" / "single_extractor_A"
PDF = REF_HTN / "AHA-ACC-2025-HBP-Guideline_JACC"


def pairs_of(rows):
    out = {}
    for r in rows:
        if not r["quotation_ok"]:
            continue
        k = (r["source"], r["target"])
        if k not in out or STRENGTH_ORDER.get(r["strength"], 0) > STRENGTH_ORDER.get(out[k]["strength"], 0):
            out[k] = dict(r)
    return out


def main():
    check_prereg()
    sett = json.loads((CKD_FREEZE / "design" / "extraction_settings_v1.json").read_text(encoding="utf-8"))
    voc = json.loads((CKD_FREEZE / "design" / "concepts_constructs_v1.json").read_text(encoding="utf-8"))
    imap = json.loads((Path(__file__).parent / "concepts_constructs_htn_v1.json").read_text(encoding="utf-8"))["concept_to_item"]["nhanes_htn"]
    props = sett["json_schema_v1"]["properties"]["edges"]["items"]["properties"]
    src_ok, dst_ok = props["source"]["enum"], props["target"]["enum"]
    pages = {"aha_acc_2025": (Path(str(PDF) + "_raw.txt").read_text(encoding="utf-8").split("\f"),
                              Path(str(PDF) + "_layout.txt").read_text(encoding="utf-8").split("\f"))}
    index = list(csv.DictReader(open(FREEZE / "chunk_index.csv", encoding="utf-8")))
    stats = defaultdict(lambda: defaultdict(int))
    rows, per_chunk = [], {}
    for r in index:
        f = A / "htn" / f"{r['chunk_id']}.txt"
        got = parse_chunk(r["chunk_id"], "aha_acc_2025", {f"raw/{r['chunk_id']}.txt": f.read_bytes()}, pages,
                          set(src_ok), set(dst_ok), voc, stats)
        rows += got
        per_chunk[r["chunk_id"]] = got
    DEST.mkdir(parents=True, exist_ok=True)
    write_rows(DEST / "aha_passages_extractorA_claude_v1.csv", rows)
    pa = pairs_of(rows)
    write_rows(DEST / "aha_pairs_extractorA_claude_v1.csv", list(pa.values()))
    BP = "BLOOD_PRESSURE"
    u70 = [(u, v) for u in src_ok for v in dst_ok if u != v and BP not in (u, v)]
    u88 = [(u, v) for u in src_ok for v in dst_ok if u != v]
    items = sorted({f"{a}->{b}" for (u, v) in pa for a in imap[u] for b in imap[v] if a != b})
    # test-retest (A only; B outputs not opened after the failed gate)
    tr = json.loads((FREEZE / "test_retest_chunks.json").read_text(encoding="utf-8"))["chunk_ids"]
    retest = {}
    for cid in tr:
        st2 = defaultdict(lambda: defaultdict(int))
        r2 = parse_chunk(cid, "aha_acc_2025", {f"raw/{cid}.txt": (A / "retest" / f"{cid}_run2.txt").read_bytes()},
                         pages, set(src_ok), set(dst_ok), voc, st2)
        s1 = {k for k in pairs_of(per_chunk[cid]) if k in u70}
        s2 = {k for k in pairs_of(r2) if k in u70}
        both = len(s1 & s2)
        retest[cid] = {"run1_pairs": sorted(map(list, s1)), "run2_pairs": sorted(map(list, s2)), "both": both,
                       "only_run1": len(s1 - s2), "only_run2": len(s2 - s1),
                       "raw_agreement_over_70": (70 - len(s1 ^ s2)) / 70,
                       "run1_text_identical_to_run2": (A / "htn" / f"{cid}.txt").read_bytes() == (A / "retest" / f"{cid}_run2.txt").read_bytes()}
    gate_b = json.loads((OUT / "a1_extraction" / "recall_gate" / "recall_gate_extractorB_qwen72b_v2.json").read_text(encoding="utf-8"))
    res = {"_about": "A1-HTN. Extractor B failed the recall gate (no fallback, addendum 5.4): HTN agreed graph, H3-HTN and "
                     "A-Q4-HTN not reached. Extractor A's quotation-checked edges reported descriptively as a "
                     "single-extractor graph; it is not used by any test.",
           "written": f"{datetime.now():%d/%m/%Y %H:%M}",
           "recall_gate": {"extractorA_claude_v1": json.loads((OUT / "a1_extraction" / "recall_gate" / "recall_gate_extractorA_claude_v1.json").read_text(encoding="utf-8"))["verdict"],
                           "extractorB_qwen72b_v2": gate_b["verdict"]},
           "agreed_graph": "not reached (extractor B failed the recall gate)",
           "extractorB_htn_outputs": "hashed, not opened: " + sha256_file(B / "outputs_sha256.txt"),
           "extractorA_parse_and_drop_counts": dict(stats["aha_acc_2025"]),
           "extractorA_passages": len(rows), "extractorA_passages_after_quote_check": sum(r["quotation_ok"] for r in rows),
           "extractorA_pairs_after_quote_check": sorted(map(list, pa)),
           "extractorA_pairs_in_70": sorted(map(list, (k for k in pa if k in u70))),
           "extractorA_pairs_in_88": sorted(map(list, (k for k in pa if k in u88))),
           "extractorA_nhanes_item_edges": items,
           "extractorA_item_edges_into_indicators": [e for e in items if e.split("->")[1] in ("GenHlth", "MentHlth")],
           "test_retest_extractorA": retest, "test_retest_extractorB": "not computed (B outputs not opened after the failed gate)"}
    write_json(DEST / "single_extractor_A.json", res)
    names = sorted(x.name for x in DEST.iterdir() if x.name != "outputs_sha256.txt")
    (DEST / "outputs_sha256.txt").write_text("".join(f"{sha256_file(DEST / n)} *{n}\n" for n in names), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("recall_gate", "extractorA_parse_and_drop_counts", "extractorA_pairs_after_quote_check",
                                          "extractorA_nhanes_item_edges", "test_retest_extractorA")}, indent=1))


if __name__ == "__main__":
    main()
