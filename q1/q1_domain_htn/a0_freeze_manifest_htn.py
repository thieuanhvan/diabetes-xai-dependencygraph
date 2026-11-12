"""A0-HTN freeze: copy the design files, hash every frozen HTN input into the A0-HTN manifest, and append the
manifest hash to prereg/MANIFEST_sha256.txt. Mirrors q1_domain_ckd/a0_freeze_manifest.py.

Stage 1 (now, before the guideline PDF exists): design files, NHANES HTN table and flow, HTN role table and lock
set, recall-gate messages of both extractors, the reused CKD frozen inputs (re-hashed and compared with the CKD A0
manifest), and the A0-HTN scripts.
Later stages (PDF, text conversions, heading index, units, chunks, rendered prompts) are appended with
  python -I a0_freeze_manifest_htn.py --append <tag> "<reason>" <file> [<file> ...]
which never rewrites earlier lines (superseded lines are marked).
Usage: python -I a0_freeze_manifest_htn.py
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I omits the script dir
from htn_common import CKD_FREEZE, FREEZE, OUT, PAPER7, TOOLS, below_normal, check_prereg, sha256_file  # noqa: E402

DESIGN = ["section_rule_htn_v1.json", "extraction_settings_htn_v1.json", "concepts_constructs_htn_v1.json"]
SCRIPTS = ["htn_common.py", "a0_nhanes_htn.py", "a0_role_table_htn.py", "a0_render_gate_prompts_v2.py",
           "a0_build_chunks_htn.py", "a0_freeze_manifest_htn.py"]
CKD_REUSED = ["design/concepts_constructs_v1.json", "design/extraction_prompt_v1_system.txt",
              "design/extraction_prompt_v1_user.txt", "design/extraction_prompt_v2_fallback_system.txt",
              "design/extraction_prompt_v2_fallback_user.txt", "design/extraction_settings_v1.json",
              "design/section_list_v1.json", "chunk_index.csv"]
MAN = FREEZE / "A0_HTN_MANIFEST_sha256.txt"
PM = PAPER7 / "prereg" / "MANIFEST_sha256.txt"


def rel(p: Path) -> str:
    return p.relative_to(PAPER7).as_posix() if p.is_relative_to(PAPER7) else p.as_posix()


def ckd_manifest() -> dict[str, str]:
    out = {}
    for line in (CKD_FREEZE / "A0_MANIFEST_sha256.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split(" *", 1)
        if len(parts) == 2 and "[SUPERSEDED" not in line:
            out[parts[1].strip()] = parts[0].strip()
    return out


def append_prereg_manifest(label: str) -> str:
    h = sha256_file(MAN)
    PM.write_text(PM.read_text(encoding="utf-8").rstrip("\n") + "\n"
                  + f"{h} *../outputs/q1_domain_htn/a0_freeze/A0_HTN_MANIFEST_sha256.txt ({label})\n",
                  encoding="utf-8", newline="\n")
    return h


def append(tag: str, reason: str, files: list[Path]) -> None:
    rels = {rel(p): p for p in files}
    out = []
    for line in MAN.read_text(encoding="utf-8").splitlines():
        parts = line.split(" *", 1)
        if len(parts) == 2 and parts[1].strip() in rels and "[SUPERSEDED" not in line:
            line += f"  [SUPERSEDED {tag}]"
        out.append(line)
    out += ["", f"## {tag} ({datetime.now():%d/%m/%Y %H:%M}): {reason}"]
    out += [f"{sha256_file(p)} *{r}" for r, p in rels.items()]
    MAN.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(MAN, append_prereg_manifest(f"A0-HTN manifest after {tag}"))


def main():
    below_normal()
    check_prereg()
    if len(sys.argv) > 1 and sys.argv[1] == "--append":
        append(sys.argv[2], sys.argv[3], [Path(f) for f in sys.argv[4:]])
        return
    assert not MAN.exists(), "stage-1 manifest exists; use --append"
    (FREEZE / "design").mkdir(parents=True, exist_ok=True)
    for f in DESIGN:
        shutil.copy2(TOOLS / f, FREEZE / "design" / f)
    ckd = ckd_manifest()
    reused = []
    for r in CKD_REUSED:
        p = CKD_FREEZE / r
        h = sha256_file(p)
        assert ckd.get(rel(p)) == h, f"CKD frozen input changed or not in CKD A0 manifest: {rel(p)}"
        reused.append(p)
    gate_chunks = sorted((CKD_FREEZE / "chunks").glob("gate_*.txt"))
    gate_v1 = sorted((CKD_FREEZE / "prompts").glob("gate_*_user.txt"))
    for p in gate_chunks + gate_v1:
        assert ckd.get(rel(p)) == sha256_file(p), rel(p)
    groups = {
        "design (unit-selection rule, extractor settings and gates, HTN Concept-to-item map)": sorted((FREEZE / "design").glob("*")),
        "CKD frozen inputs reused unchanged (hash equal to the CKD A0 manifest)": reused,
        "recall-gate chunks reused (CKD freeze, hash-checked)": gate_chunks,
        "recall-gate user messages, extractor A (CKD v1, hash-checked)": gate_v1,
        "recall-gate user messages, extractor B (v2 rendered for HTN)": sorted((FREEZE / "prompts_gate_v2").glob("*.txt"))
        + [FREEZE / "gate_prompts_index.json"],
        "NHANES HTN analytic table, flow and gate": sorted((OUT / "a0_nhanes_htn").glob("*")),
        "HTN role table and lock set (before any model)": sorted((OUT / "a0_role_table").glob("*")),
        "A0-HTN scripts": [TOOLS / s for s in SCRIPTS],
    }
    lines = [f"# A0-HTN manifest, P7 hypertension domain (addendum HTN v1; prereg v3 95a83da5...), written {datetime.now():%d/%m/%Y %H:%M}",
             "# Stage 1: frozen before the guideline PDF was obtained and before any extraction output, model fit or counterfactual existed.", ""]
    for g, fs in groups.items():
        lines.append(f"## {g}")
        lines += [f"{sha256_file(p)} *{rel(p)}" for p in fs if p.is_file()]
        lines.append("")
    MAN.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(MAN, append_prereg_manifest("A0-HTN freeze manifest, stage 1"))


if __name__ == "__main__":
    main()
