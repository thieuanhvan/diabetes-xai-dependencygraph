"""A0-HTN: render extractor B's (prompt v2) user messages for the 18 frozen recall-gate chunks.

In CKD only extractor 2 (Qwen) was run on the recall gate; the two Claude prompts were never gate-tested. For HTN
both Claude extractors pass the gate first (addendum HTN v1, section 5). Extractor A uses the frozen v1 gate user
messages of the CKD freeze unchanged; this script fills the frozen v2 template for the same chunks (placeholders
replaced literally, as a1_fallback_render_prompts.py). Every input is checked against the CKD A0 manifest.
Reads CKD files only; writes only under outputs/q1_domain_htn/a0_freeze/prompts_gate_v2/.
Usage: python -I a0_render_gate_prompts_v2.py
"""
from __future__ import annotations

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I omits the script dir
from htn_common import CKD_FREEZE, FREEZE, PAPER7, check_prereg, sha256_file, write_json  # noqa: E402

DEST = FREEZE / "prompts_gate_v2"


def ckd_manifest() -> dict[str, str]:
    out = {}
    for line in (CKD_FREEZE / "A0_MANIFEST_sha256.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split(" *", 1)
        if len(parts) == 2 and "[SUPERSEDED" not in line:
            out[parts[1].strip()] = parts[0].strip()
    return out


def checked(p, man):
    rel = p.relative_to(PAPER7).as_posix()
    h = sha256_file(p)
    assert man.get(rel) == h, f"not in CKD A0 manifest or changed: {rel}"
    return h


def main():
    check_prereg()
    man = ckd_manifest()
    design = CKD_FREEZE / "design"
    for f in ("extraction_settings_v1.json", "section_list_v1.json", "extraction_prompt_v2_fallback_user.txt",
              "extraction_prompt_v1_user.txt", "extraction_prompt_v1_system.txt", "extraction_prompt_v2_fallback_system.txt"):
        checked(design / f, man)
    checked(CKD_FREEZE / "chunk_index.csv", man)
    sett = json.loads((design / "extraction_settings_v1.json").read_text(encoding="utf-8"))
    docs = {d["unit"]: d for d in json.loads((design / "section_list_v1.json").read_text(encoding="utf-8"))["recall_gate"]["documents"]}
    tmpl = (design / "extraction_prompt_v2_fallback_user.txt").read_text(encoding="utf-8")
    index = [r for r in csv.DictReader(open(CKD_FREEZE / "chunk_index.csv", encoding="utf-8")) if r["document"] in docs]
    assert len(index) == 18, len(index)
    DEST.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in index:
        cp = CKD_FREEZE / "chunks" / f"{r['chunk_id']}.txt"
        h = checked(cp, man)
        assert h == r["sha256_chunk"]
        h_v1 = checked(CKD_FREEZE / "prompts" / f"{r['chunk_id']}_user.txt", man)
        d = docs[r["document"]]
        msg = (tmpl.replace("{DOCUMENT_LABEL}", d["label"]).replace("{LICENCE}", sett["licence_notices"][r["document"]])
               .replace("{UNIT_LABEL}", d["label"] + " (whole document)").replace("{CHUNK_ID}", r["chunk_id"])
               .replace("{CHUNK}", r["chunk"]).replace("{N_CHUNKS}", r["n_chunks"])
               .replace("{CHUNK_TEXT}", cp.read_text(encoding="utf-8").rstrip("\n")))
        out = DEST / f"{r['chunk_id']}_user.txt"
        out.write_text(msg, encoding="utf-8", newline="\n")
        rows.append({"chunk_id": r["chunk_id"], "sha256_chunk": h, "sha256_user_v1_ckd_freeze": h_v1,
                     "sha256_user_v2": sha256_file(out)})
    write_json(FREEZE / "gate_prompts_index.json", {
        "_about": "Recall-gate user messages for both HTN extractors (addendum HTN v1, section 5). A = CKD frozen v1 "
                  "messages (a0_freeze/prompts/<chunk>_user.txt of the CKD freeze); B = v2 template rendered here.",
        "chunks": rows})
    print(len(rows), "gate messages (v2) written to", DEST)


if __name__ == "__main__":
    main()
