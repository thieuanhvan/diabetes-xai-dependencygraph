"""Render the fallback extractor's user messages (prereg v3 4.4 recall-gate fallback, deviations log E1).

The recall gate of extractor 2 (Qwen2.5-7B) failed, so the fallback fixed in v2 applies: a second Claude instance
with an independently written second prompt (a0_freeze/design/extraction_prompt_v2_fallback_{system,user}.txt).
This script checks every KDIGO chunk against the A0 manifest, fills the v2 user template for the 11 KDIGO chunks
(placeholders replaced literally, no str.format) and writes a0_freeze/prompts_v2_fallback/<chunk>_user.txt plus a
settings record. It does not read the v1 prompt files or any extraction output.
Usage: python -I a1_fallback_render_prompts.py
"""
from __future__ import annotations

import csv
import json

from q1_common import FREEZE, PAPER7, check_prereg, sha256_file, write_json

DESIGN = FREEZE / "design"
DEST = FREEZE / "prompts_v2_fallback"
DOC_LABEL = "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease"


def manifest_hashes() -> dict[str, str]:
    out = {}
    for line in (FREEZE / "A0_MANIFEST_sha256.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split(" *", 1)
        if len(parts) == 2 and "[SUPERSEDED" not in line:
            out[parts[1].strip()] = parts[0].strip()
    return out


def main():
    check_prereg()
    man = manifest_hashes()
    sett = json.loads((DESIGN / "extraction_settings_v1.json").read_text(encoding="utf-8"))
    sl = json.loads((DESIGN / "section_list_v1.json").read_text(encoding="utf-8"))["kdigo"]
    labels = {u["unit"]: u["label"] for u in sl["section_units"] + sl["table_units"]}
    tmpl = (DESIGN / "extraction_prompt_v2_fallback_user.txt").read_text(encoding="utf-8")
    index = [r for r in csv.DictReader(open(FREEZE / "chunk_index.csv", encoding="utf-8")) if r["document"] == "kdigo"]
    DEST.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in index:
        cp = FREEZE / "chunks" / f"{r['chunk_id']}.txt"
        rel = cp.relative_to(PAPER7).as_posix()
        h = sha256_file(cp)
        assert h == r["sha256_chunk"] == man[rel], f"chunk hash mismatch: {rel}"
        text = cp.read_text(encoding="utf-8")
        msg = (tmpl.replace("{DOCUMENT_LABEL}", DOC_LABEL).replace("{LICENCE}", sett["licence_notices"]["kdigo"])
               .replace("{UNIT_LABEL}", labels[r["unit"]]).replace("{CHUNK_ID}", r["chunk_id"])
               .replace("{CHUNK}", r["chunk"]).replace("{N_CHUNKS}", r["n_chunks"])
               .replace("{CHUNK_TEXT}", text.rstrip("\n")))
        out = DEST / f"{r['chunk_id']}_user.txt"
        out.write_text(msg, encoding="utf-8", newline="\n")
        rows.append({"chunk_id": r["chunk_id"], "sha256_chunk": h, "sha256_user_v2": sha256_file(out)})
    write_json(DESIGN / "extraction_settings_v2_fallback.json", {
        "_about": "Fallback extractor (prereg v3 4.4: recall gate of extractor 2 failed). Second Claude instance with an "
                  "independently written prompt; written before any fallback extraction.",
        "prompt_files": {"system": "extraction_prompt_v2_fallback_system.txt",
                         "user_template": "extraction_prompt_v2_fallback_user.txt"},
        "rendered_user_messages": "a0_freeze/prompts_v2_fallback/<chunk_id>_user.txt",
        "extractor_2_fallback": {
            "name": "Claude, second instance (fallback for extractor 2)", "model": "claude-opus-5-5",
            "runtime": "Claude Code agent sessions, one fresh sub-agent per chunk, given only the v2 system prompt and "
                       "the rendered user message; temperature and max_tokens not controllable (as D2)",
            "session_rule": "no access to extractor 1 prompt or output, extractor 2 (Qwen) output, the prereg or the "
                            "pre-plan check"},
        "json_schema": "json_schema_v1 of extraction_settings_v1.json (unchanged)",
        "parsing_rule": "as extraction_settings_v1.json", "merge_rule": "as extraction_settings_v1.json",
        "chunks": rows})
    print(len(rows), "user messages written to", DEST)


if __name__ == "__main__":
    main()
