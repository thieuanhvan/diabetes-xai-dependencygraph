"""A1-HTN recall gate (addendum HTN v3, Section 5.4): score one extractor's outputs on the 18 frozen gate chunks.

Rule (copied from prereg v3 4.4 / CKD a1_ingest_kaggle_zip.py, frozen parsing and quotation check reused read-only):
pass iff the HEARTS-D agreed edge and >= 3 of the 5 MoH 5481 agreed edges (BRFSS items, P7 X5 agreed graph) are
recovered with at least one passage that passes the quotation check; NG28 output reported as a false-positive count.
Inputs: <folder>/<chunk_id>.txt = the extractor's raw reply text for that chunk (one run, run policy of Section 5.3).
Usage: python -I a1_gate_htn.py <extractor_name> <folder>
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from htn_common import CKD_FREEZE, CKD_TOOLS, OUT, below_normal, check_prereg, sha256_file, write_json  # noqa: E402

sys.path.insert(0, str(CKD_TOOLS))
from a1_ingest_kaggle_zip import TEXT, X5, X5_PREFIX, parse_chunk  # noqa: E402  (frozen CKD code, read only)

DEST = OUT / "a1_extraction" / "recall_gate"


def main():
    below_normal()
    check_prereg()
    name, folder = sys.argv[1], Path(sys.argv[2])
    sett = json.loads((CKD_FREEZE / "design" / "extraction_settings_v1.json").read_text(encoding="utf-8"))
    voc = json.loads((CKD_FREEZE / "design" / "concepts_constructs_v1.json").read_text(encoding="utf-8"))
    props = sett["json_schema_v1"]["properties"]["edges"]["items"]["properties"]
    src_ok, dst_ok = set(props["source"]["enum"]), set(props["target"]["enum"])
    index = [r for r in csv.DictReader(open(CKD_FREEZE / "chunk_index.csv", encoding="utf-8")) if r["document"] != "kdigo"]
    assert len(index) == 18
    pages = {k: (Path(str(p) + "_raw.txt").read_text(encoding="utf-8").split("\f"),
                 Path(str(p) + "_layout.txt").read_text(encoding="utf-8").split("\f")) for k, p in TEXT.items()}
    stats = defaultdict(lambda: defaultdict(int))
    passages, hashes = [], {}
    for r in index:
        f = folder / f"{r['chunk_id']}.txt"
        hashes[r["chunk_id"]] = sha256_file(f)
        files = {f"raw/{r['chunk_id']}.txt": f.read_bytes()}
        passages += parse_chunk(r["chunk_id"], r["document"], files, pages, src_ok, dst_ok, voc, stats)
    m = voc["concept_to_item"]["brfss"]

    def items(rows, need_quote):
        out = set()
        for p in rows:
            if need_quote and not p["quotation_ok"]:
                continue
            for a in m[p["source"]]:
                for b in m[p["target"]]:
                    if a != b:
                        out.add((a, b))
        return out

    gate = {}
    for doc in X5_PREFIX:
        A = list(csv.DictReader(open(X5 / f"{X5_PREFIX[doc]}_extractor_A.csv", encoding="utf-8")))
        B = {(x["src"], x["dst"]) for x in csv.DictReader(open(X5 / f"{X5_PREFIX[doc]}_extractor_B.csv", encoding="utf-8"))}
        agreed = {(x["src"], x["dst"]) for x in A if (x["src"], x["dst"]) in B}
        rows = [p for p in passages if p["document"] == doc]
        got_q, got_all = items(rows, True), items(rows, False)
        gate[doc] = {"agreed_x5": sorted(map(list, agreed)), "recovered_after_quote_check": sorted(map(list, agreed & got_q)),
                     "recovered_before_quote_check": sorted(map(list, agreed & got_all)),
                     "extra_pairs_after_quote_check": len(got_q - agreed), "extra_pairs_before_quote_check": len(got_all - agreed)}
    who, moh = gate["gate_who_heartsd"], gate["gate_moh5481"]
    passed = (len(who["recovered_after_quote_check"]) == len(who["agreed_x5"]) == 1
              and len(moh["recovered_after_quote_check"]) >= 3)
    res = {"extractor": name, "verdict": "PASS" if passed else "FAIL", "gate": gate,
           "ng28_false_positive_pairs_after_quote_check": gate["gate_nice_ng28"]["extra_pairs_after_quote_check"],
           "parse_and_drop_counts": {k: dict(v) for k, v in stats.items()}, "output_sha256": hashes}
    DEST.mkdir(parents=True, exist_ok=True)
    write_json(DEST / f"recall_gate_{name}.json", res)
    with open(DEST / f"gate_passages_{name}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(passages[0]) if passages else ["chunk_id"], lineterminator="\n")
        w.writeheader()
        w.writerows(passages)
    print(json.dumps({k: res[k] for k in ("extractor", "verdict", "ng28_false_positive_pairs_after_quote_check")}),
          json.dumps({d: (len(g["recovered_after_quote_check"]), len(g["agreed_x5"])) for d, g in gate.items()}))


if __name__ == "__main__":
    main()
