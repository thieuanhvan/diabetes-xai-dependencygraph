"""Ingest the zip returned by the Kaggle notebook (extractor 2, Qwen2.5-7B) and continue the pipeline.

NOT RUN in A0. Steps:
  1 verify the zip: every file against outputs_sha256.txt; run_manifest settings/inputs hashes against the frozen
    A0 files; llama.cpp commit f3b407ca1; GGUF hashes; prompt token counts equal to the frozen chunk_index;
  2 parse each chunk output (first JSON object; unparseable -> zero edges, counted), drop out-of-vocabulary ids,
    u == v and not-recorded targets (counted);
  3 quotation check (prereg 4.4, fixed): tokens lower-cased and stripped of punctuation; pass if contiguous in the
    -raw text of the cited page, or in order within a window of three consecutive lines of the -layout text of
    that page; a failing quotation drops that passage of this extractor only; drop counts reported;
  4 recall gate (prereg 4.4), evaluated on these GPU outputs: map Concepts to BRFSS items; pass if the HEARTS-D
    agreed edge and >= 3 of the 5 MoH agreed edges are recovered (with at least one passage that passes the
    quotation check); NG28 edges reported as a false-positive count; recall before the quotation check also shown;
  5 only if the gate passes: write extractor-2 KDIGO edges (concept pairs and per-passage rows) for the agreement
    step; if it fails, KDIGO outputs of extractor 2 are not opened and the v2 fallback (second Claude instance,
    independently written prompt) applies.
Usage: python -I a1_ingest_kaggle_zip.py <path to p7_qwen_outputs.zip>
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

from q1_common import FREEZE, OUT, PAPER7, REF_GATE, REF_KDIGO, TOOLS, below_normal, check_prereg, sha256_file, write_json

DEST = OUT / "a1_extraction" / "extractor2_qwen"
STRENGTH_ORDER = {"graded": 3, "explicit": 2, "narrative": 1}
X5 = PAPER7 / "killtest_x5" / "extraction"
TEXT = {"kdigo": REF_KDIGO / "KDIGO-2024-CKD-Guideline",
        "gate_who_heartsd": REF_GATE / "WHO_HEARTS-D_2020_en",
        "gate_moh5481": REF_GATE / "QD_5481_QD-BYT_2020_HD_DTD_tip2",
        "gate_nice_ng28": REF_GATE / "NICE_NG28_2022_NBK553486"}
X5_PREFIX = {"gate_who_heartsd": "who_heartsd", "gate_moh5481": "byt5481", "gate_nice_ng28": "nice_ng28"}


def norm_tokens(s: str) -> list[str]:
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return s.split()


def contiguous(needle: list[str], hay: list[str]) -> bool:
    n = len(needle)
    return n > 0 and any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def in_order(needle: list[str], hay: list[str]) -> bool:
    it = iter(hay)
    return len(needle) > 0 and all(t in it for t in needle)


def quotation_ok(q: str, page: int, raw_pages, layout_pages) -> bool:
    toks = norm_tokens(q)
    if not toks or len(toks) > 12 or not (1 <= page <= len(raw_pages)):
        return False
    if contiguous(toks, norm_tokens(raw_pages[page - 1])):
        return True
    lines = layout_pages[page - 1].splitlines()
    for i in range(len(lines)):
        if in_order(toks, norm_tokens(" ".join(lines[i:i + 3]))):
            return True
    return False


def first_json(s: str):
    i = s.find("{")
    while i != -1:
        try:
            obj, _ = json.JSONDecoder().raw_decode(s[i:])
            return obj
        except json.JSONDecodeError:
            i = s.find("{", i + 1)
    return None


def main():
    below_normal()
    check_prereg()
    zpath = Path(sys.argv[1])
    sett = json.loads((TOOLS / "extraction_settings_v1.json").read_text(encoding="utf-8"))
    voc = json.loads((TOOLS / "concepts_constructs_v1.json").read_text(encoding="utf-8"))
    src_ok = set(sett["json_schema_v1"]["properties"]["edges"]["items"]["properties"]["source"]["enum"])
    dst_ok = set(sett["json_schema_v1"]["properties"]["edges"]["items"]["properties"]["target"]["enum"])
    index = {r["chunk_id"]: r for r in csv.DictReader(open(FREEZE / "chunk_index.csv", encoding="utf-8"))}
    kag = PAPER7 / "kaggle" / "dataset_p7_qwen_inputs"

    # 1 verification
    with zipfile.ZipFile(zpath) as z:
        files = {n: z.read(n) for n in z.namelist()}
    listed = dict((l.split(None, 1)[1].lstrip("*"), l.split(None, 1)[0])
                  for l in files["outputs_sha256.txt"].decode().splitlines() if l.strip())
    for n, h in listed.items():
        assert hashlib.sha256(files[n]).hexdigest() == h, f"hash mismatch in zip: {n}"
    man = json.loads(files["run_manifest.json"])
    assert man["llama_cpp_commit"].startswith("f3b407ca1"), man["llama_cpp_commit"]
    assert man["settings_sha256"] == sha256_file(kag / "extraction_settings_v1.json")
    assert man["inputs_manifest_sha256"] == sha256_file(kag / "inputs_manifest_sha256.txt")
    assert man["model_files"] == sett["extractor_2"]["model_files"]
    for c in man["chunks"]:
        assert c["prompt_tokens_server"] == c["prompt_tokens_frozen"] == int(index[c["chunk_id"]]["prompt_tokens"]), c
    assert {c["chunk_id"] for c in man["chunks"]} == set(index), "chunk set differs from the frozen index"
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "zip_sha256.txt").write_text(f"{sha256_file(zpath)} *{zpath.name}\n", encoding="utf-8")

    pages = {k: ((Path(str(p) + "_raw.txt")).read_text(encoding="utf-8").split("\f"),
                 (Path(str(p) + "_layout.txt")).read_text(encoding="utf-8").split("\f")) for k, p in TEXT.items()}
    stats = defaultdict(lambda: defaultdict(int))
    passages = []
    gate_docs = set(X5_PREFIX)
    for cid, r in sorted(index.items()):
        doc = r["document"]
        if doc == "kdigo":
            continue  # KDIGO outputs are opened only after the gate passes (step 5)
        passages += parse_chunk(cid, doc, files, pages, src_ok, dst_ok, voc, stats)

    # 4 recall gate
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
    for doc in gate_docs:
        A = list(csv.DictReader(open(X5 / f"{X5_PREFIX[doc]}_extractor_A.csv", encoding="utf-8")))
        B = {(x["src"], x["dst"]) for x in csv.DictReader(open(X5 / f"{X5_PREFIX[doc]}_extractor_B.csv", encoding="utf-8"))}
        agreed = {(x["src"], x["dst"]) for x in A if (x["src"], x["dst"]) in B}
        rows = [p for p in passages if p["document"] == doc]
        got_q, got_all = items(rows, True), items(rows, False)
        gate[doc] = {"agreed_x5": sorted(map(list, agreed)), "recovered_after_quote_check": sorted(map(list, agreed & got_q)),
                     "recovered_before_quote_check": sorted(map(list, agreed & got_all)),
                     "extra_pairs_after_quote_check": len(got_q - agreed), "extra_pairs_before_quote_check": len(got_all - agreed)}
    who = gate["gate_who_heartsd"]
    moh = gate["gate_moh5481"]
    passed = (len(who["recovered_after_quote_check"]) == len(who["agreed_x5"]) == 1
              and len(moh["recovered_after_quote_check"]) >= 3)
    gate["verdict"] = "PASS" if passed else "FAIL"
    gate["ng28_false_positive_pairs_after_quote_check"] = gate["gate_nice_ng28"]["extra_pairs_after_quote_check"]
    write_json(DEST / "recall_gate.json", {"gate": gate, "parse_and_drop_counts": {k: dict(v) for k, v in stats.items()},
                                           "run_manifest_gpu": man["gpu"], "nvcc": man["nvcc"]})
    print(json.dumps(gate, indent=1))
    if not passed:
        print("Recall gate FAILED: KDIGO outputs of extractor 2 are not used; apply the v2 fallback.")
        return

    # 5 KDIGO edges of extractor 2
    kd = []
    for cid, r in sorted(index.items()):
        if r["document"] == "kdigo":
            kd += parse_chunk(cid, "kdigo", files, pages, src_ok, dst_ok, voc, stats)
    write_rows(DEST / "kdigo_passages_extractor2.csv", kd)
    pairs = {}
    for p in kd:
        if not p["quotation_ok"]:
            continue
        k = (p["source"], p["target"])
        if k not in pairs or STRENGTH_ORDER[p["strength"]] > STRENGTH_ORDER[pairs[k]["strength"]]:
            pairs[k] = dict(p)
    write_rows(DEST / "kdigo_pairs_extractor2.csv", list(pairs.values()))
    write_json(DEST / "kdigo_drop_counts.json", {k: dict(v) for k, v in stats.items()})
    print("KDIGO pairs (extractor 2, after quotation check):", len(pairs))


def parse_chunk(cid, doc, files, pages, src_ok, dst_ok, voc, stats):
    raw_pages, layout_pages = pages[doc]
    out = files[f"raw/{cid}.txt"].decode("utf-8")
    obj = first_json(out)
    st = stats[doc]
    if not isinstance(obj, dict) or not isinstance(obj.get("edges"), list):
        st["unparseable_chunks"] += 1
        return []
    rows = []
    for e in obj["edges"]:
        st["edges_returned"] += 1
        s, t = e.get("source"), e.get("target")
        if s not in src_ok or t not in dst_ok:
            st["dropped_vocabulary"] += 1
            continue
        if s == t:
            st["dropped_self_loop"] += 1
            continue
        try:
            pg = int(e.get("page"))
        except (TypeError, ValueError):
            pg = -1
        ok = quotation_ok(str(e.get("quotation", "")), pg, raw_pages, layout_pages)
        st["quotation_fail"] += int(not ok)
        rows.append({"document": doc, "chunk_id": cid, "source": s, "target": t, "strength": e.get("strength"),
                     "grade": e.get("grade", ""), "page": pg, "section": e.get("section", ""),
                     "quotation": e.get("quotation", ""), "paraphrase": e.get("paraphrase", ""),
                     "population": e.get("population", ""), "quotation_ok": ok})
    return rows


def write_rows(path, rows):
    cols = ["document", "chunk_id", "source", "target", "strength", "grade", "page", "section", "quotation",
            "paraphrase", "population", "quotation_ok"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
