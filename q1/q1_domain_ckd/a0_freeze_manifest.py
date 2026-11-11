"""A0: copy the frozen design files, write the A0 manifest (SHA-256 of every frozen input) and the Kaggle dataset folder.

Outputs:
  outputs/q1_domain_ckd/a0_freeze/design/             prompts, settings, Concept/construct tables, section list
  outputs/q1_domain_ckd/a0_freeze/A0_MANIFEST_sha256.txt
  paper7/kaggle/dataset_p7_qwen_inputs/               only what the Kaggle notebook reads (no NHANES, no restricted data)
  paper7/prereg/MANIFEST_sha256.txt                   one line appended with the A0 manifest hash
Usage: python -I a0_freeze_manifest.py
"""
from __future__ import annotations

import shutil
from datetime import datetime

from q1_common import (FREEZE, NHANES_NEW_RAW, OUT, PAPER7, REF_GATE, REF_KDIGO, TOOLS, below_normal, check_prereg,
                       sha256_file)

DESIGN = ["extraction_prompt_v1_system.txt", "extraction_prompt_v1_user.txt", "extraction_settings_v1.json",
          "concepts_constructs_v1.json", "section_list_v1.json"]
SCRIPTS = ["q1_common.py", "a0_build_chunks.py", "a0_nhanes_ckd.py", "a0_role_table.py", "a0_freeze_manifest.py",
           "make_kaggle_notebook.py", "a1_ingest_kaggle_zip.py"]
KAG = PAPER7 / "kaggle" / "dataset_p7_qwen_inputs"


def main():
    below_normal()
    check_prereg()
    (FREEZE / "design").mkdir(parents=True, exist_ok=True)
    for f in DESIGN:
        shutil.copy2(TOOLS / f, FREEZE / "design" / f)
    groups = {
        "design (frozen prompt, settings, Concept and construct tables, section list)": sorted((FREEZE / "design").glob("*")),
        "extraction units": sorted((FREEZE / "units").glob("*.txt")),
        "chunks (identical for both extractors)": sorted((FREEZE / "chunks").glob("*.txt")),
        "rendered prompts (user message for both; ChatML for the local model)": sorted((FREEZE / "prompts").glob("*.txt")),
        "chunk index and source record": [FREEZE / "chunk_index.csv", FREEZE / "sources" / "sources.json"],
        "guideline PDFs, text conversions and licence records": sorted(REF_KDIGO.glob("*")) + sorted(REF_GATE.glob("*")),
        "NHANES public files downloaded in A0 (wwwn.cdc.gov)": sorted(NHANES_NEW_RAW.rglob("*.xpt")),
        "NHANES CKD analytic table and flow": sorted((OUT / "a0_nhanes_ckd").glob("*")),
        "CKD role table and lock set (before any model)": sorted((OUT / "a0_role_table").glob("*")),
        "CVD replication gate": sorted((OUT.parent / "q1_domain_cvd").glob("*.json")),
        "A0 scripts": [TOOLS / s for s in SCRIPTS] + [TOOLS.parent / "q1_domain_cvd" / "a0_brfss_gate.py"],
        "Kaggle notebook": [PAPER7 / "kaggle" / "p7_qwen_extraction.ipynb"],
    }
    lines = [f"# A0 manifest, P7 Q1 extension (prereg v3 95a83da5...), written {datetime.now():%d/%m/%Y %H:%M}",
             "# Every file below was frozen before any extraction output, model fit or counterfactual existed.", ""]
    for g, fs in groups.items():
        lines.append(f"## {g}")
        for p in fs:
            if p.is_file():
                rel = p.relative_to(PAPER7) if p.is_relative_to(PAPER7) else p
                lines.append(f"{sha256_file(p)} *{rel.as_posix() if hasattr(rel, 'as_posix') else rel}")
        lines.append("")
    man = FREEZE / "A0_MANIFEST_sha256.txt"
    man.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    # Kaggle dataset folder: settings, chunk index, ChatML prompts only
    if KAG.exists():
        shutil.rmtree(KAG)
    (KAG / "prompts").mkdir(parents=True)
    shutil.copy2(TOOLS / "extraction_settings_v1.json", KAG / "extraction_settings_v1.json")
    shutil.copy2(FREEZE / "chunk_index.csv", KAG / "chunk_index.csv")
    for p in sorted((FREEZE / "prompts").glob("*_chatml.txt")):
        shutil.copy2(p, KAG / "prompts" / p.name)
    kl = ["# SHA-256 of every file the Kaggle notebook reads (P7 Q1 A0)"]
    for p in sorted(KAG.rglob("*")):
        if p.is_file() and p.name != "inputs_manifest_sha256.txt":
            kl.append(f"{sha256_file(p)} *{p.relative_to(KAG).as_posix()}")
    (KAG / "inputs_manifest_sha256.txt").write_text("\n".join(kl) + "\n", encoding="utf-8", newline="\n")

    pm = PAPER7 / "prereg" / "MANIFEST_sha256.txt"
    entry = f"{sha256_file(man)} *../outputs/q1_domain_ckd/a0_freeze/A0_MANIFEST_sha256.txt (A0 freeze manifest)"
    txt = pm.read_text(encoding="utf-8")
    txt = "\n".join(l for l in txt.splitlines() if "A0_MANIFEST_sha256.txt" not in l) + "\n" + entry + "\n"
    pm.write_text(txt, encoding="utf-8", newline="\n")
    print(man, sha256_file(man))
    print(KAG / "inputs_manifest_sha256.txt", sha256_file(KAG / "inputs_manifest_sha256.txt"))


if __name__ == "__main__":
    main()
