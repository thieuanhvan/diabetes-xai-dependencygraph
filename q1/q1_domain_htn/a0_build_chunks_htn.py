"""A0-HTN: text conversions, heading index, keyword-selected units, chunks and rendered prompts (addendum HTN v1, s5).

Run only after anh Van has placed the guideline PDF in paper7/references/q1_htn/ (automated download was refused
by the publishers' bot protection; see references/q1_htn/README.md). Two stages:

  1 --index-only : pdftotext -raw/-layout next to the PDF, then write the detected heading index and the units the
                   frozen keyword rule selects (section_rule_htn_v1.json). Nothing is chunked. The index is compared
                   with the printed table of contents; footer regexes and any correction are logged as clarifications
                   in prereg/deviations_log_q1_en.md BEFORE stage 2.
  2 --port N     : needs a llama.cpp b12283 llama-server with the Qwen2.5-7B GGUF (tokeniser only, no generation;
                   counts as one heavy process). Cuts units, chunks them by the CKD rule (6,000/500 tokens,
                   line-snapped), renders the user messages of both extractors and writes chunk_index.csv.

Footer/header lines are removed with --footer-regex (repeatable), fixed at stage 1 and recorded in the output.
Writes under outputs/q1_domain_htn/a0_freeze/. Reads CKD frozen prompts (hash-checked) and never writes there.
Front matter is excluded with --min-pdf-page and the reference list with --body-end-regex (both fixed at stage 1).
Usage: python -I a0_build_chunks_htn.py --pdf <file> --index-only [--min-pdf-page P] [--footer-regex R ...]
       python -I a0_build_chunks_htn.py --pdf <file> --port 8089 [--footer-regex R ...]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I omits the script dir
from htn_common import CKD_FREEZE, CKD_TOOLS, FREEZE, TOOLS, below_normal, check_prereg, sha256_file, sha256_text, write_json  # noqa: E402

MAX_TOK, OVERLAP, CTX, N_PREDICT = 6000, 500, 16384, 2048


def pdftotext(pdf: Path) -> dict:
    res = {}
    for mode in ("raw", "layout"):
        out = pdf.parent / f"{pdf.stem}_{mode}.txt"
        subprocess.run(["pdftotext", f"-{mode}", "-enc", "UTF-8", str(pdf), str(out)], check=True)
        res[mode] = out
    return res


def flat_lines(raw_pages, footers):
    flat = []
    for i, p in enumerate(raw_pages, 1):
        for ln in p.splitlines():
            s = ln.rstrip()
            if any(f.match(s.strip()) for f in footers):
                continue
            flat.append((i, s))
    return flat


def heading_index(flat, rule):
    rx = re.compile(rule["heading_detection"]["pattern"])
    heads = []
    for k, (pg, ln) in enumerate(flat):
        m = rx.match(ln.strip())
        if m:
            num, title = m.group(1), m.group(2).strip()
            heads.append({"line": k, "pdf_page": pg, "number": num, "level": num.count(".") + 1, "title": title})
    return heads


def select_units(heads, flat_len, rule):
    sel = rule["selection_rule"]
    kws = [w.lower() for w in sel["keywords_lever_and_behaviour"] + sel["keywords_health_status"]]
    units, covered_until = [], -1
    for i, h in enumerate(heads):
        hit = [w for w in kws if w in h["title"].lower()]
        h["keyword_hits"] = hit
        if not hit or h["line"] < covered_until:
            continue
        end = next((g["line"] for g in heads[i + 1:] if g["level"] <= h["level"]), flat_len)
        units.append({"unit": "htn_s" + h["number"].replace(".", "_"), "label": f"{h['number']} {h['title']}",
                      "start_line": h["line"], "end_line": end, "keyword_hits": hit})
        covered_until = end
    return units


def marked(lines_by_page):
    out = []
    for pg, lines in lines_by_page:
        if lines:
            out.append(f"=== PDF page {pg} ===")
            out.extend(lines)
    return "\n".join(out).strip() + "\n"


def unit_text(flat, u):
    by_page = []
    for pg, ln in flat[u["start_line"]:u["end_line"]]:
        if not by_page or by_page[-1][0] != pg:
            by_page.append((pg, []))
        by_page[-1][1].append(ln)
    return marked(by_page)


def main():
    below_normal()
    check_prereg()
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--index-only", action="store_true")
    ap.add_argument("--port", type=int)
    ap.add_argument("--footer-regex", action="append", default=[])
    ap.add_argument("--body-end-regex", default=r"^References$", help="first line of the reference list")
    ap.add_argument("--min-pdf-page", type=int, default=1, help="first PDF page of the main body (front matter excluded)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    rule = json.loads((TOOLS / "section_rule_htn_v1.json").read_text(encoding="utf-8"))
    sett = json.loads((TOOLS / "extraction_settings_htn_v1.json").read_text(encoding="utf-8"))
    pdf = Path(a.pdf)
    texts = pdftotext(pdf)
    raw_pages = texts["raw"].read_text(encoding="utf-8").split("\f")
    flat = [x for x in flat_lines(raw_pages, [re.compile(r) for r in a.footer_regex]) if x[0] >= a.min_pdf_page]
    body_end = next((k for k, (_, ln) in enumerate(flat) if re.match(a.body_end_regex, ln.strip())), len(flat))
    heads = [h for h in heading_index(flat, rule) if h["line"] < body_end]
    units = select_units(heads, body_end, rule)
    (FREEZE / "units").mkdir(parents=True, exist_ok=True)
    write_json(FREEZE / "heading_index.json", {
        "pdf": str(pdf), "pdf_sha256": sha256_file(pdf), "footer_regex": a.footer_regex, "min_pdf_page": a.min_pdf_page, "body_end_regex": a.body_end_regex,
        "body_end_line": body_end, "headings": heads, "selected_units": units,
        "raw_txt_sha256": sha256_file(texts["raw"]), "layout_txt_sha256": sha256_file(texts["layout"]),
        "pdftotext": subprocess.run(["pdftotext", "-v"], capture_output=True, text=True).stderr.splitlines()[0]})
    for h in heads:
        print(("*" if h.get("keyword_hits") else " "), h["pdf_page"], h["number"], h["title"][:90], h.get("keyword_hits", ""))
    print("selected units:", [u["label"] for u in units])
    if a.index_only:
        return
    if a.port is None:
        sys.exit("stage 2 needs --port (llama-server tokeniser)")

    sys.path.insert(0, str(CKD_TOOLS))
    from a0_build_chunks import chunk, tok_count  # CKD chunker, frozen rule C1 (read only)
    prompts = {}
    for ext in ("extractor_A", "extractor_B"):
        for part in ("system_prompt", "user_template"):
            spec = sett[ext][part]
            p = CKD_FREEZE / "design" / Path(spec["file"]).name
            assert sha256_file(p) == spec["sha256"], p
            prompts[(ext, part)] = p.read_text(encoding="utf-8")
    ckd_sett = json.loads((CKD_FREEZE / "design" / "extraction_settings_v1.json").read_text(encoding="utf-8"))
    for d in ("chunks", "prompts_A_v1", "prompts_B_v2"):
        (FREEZE / d).mkdir(parents=True, exist_ok=True)
    rows = []
    for u in units:
        txt = unit_text(flat, u)
        (FREEZE / "units" / f"{u['unit']}.txt").write_text(txt, encoding="utf-8", newline="\n")
        cs = chunk(a.port, txt)
        for i, c in enumerate(cs, 1):
            cid = f"{u['unit']}_c{i:02d}"
            (FREEZE / "chunks" / f"{cid}.txt").write_text(c, encoding="utf-8", newline="\n")
            ua = (prompts[("extractor_A", "user_template")].replace("{DOCUMENT_LABEL}", sett["document_label"])
                  .replace("{LICENCE_NOTICE}", sett["licence_notice"]).replace("{UNIT_LABEL}", u["label"])
                  .replace("{CHUNK_INDEX}", str(i)).replace("{CHUNK_COUNT}", str(len(cs)))
                  .replace("{CHUNK_TEXT}", c.rstrip("\n")))
            ub = (prompts[("extractor_B", "user_template")].replace("{DOCUMENT_LABEL}", sett["document_label"])
                  .replace("{LICENCE}", sett["licence_notice"]).replace("{UNIT_LABEL}", u["label"])
                  .replace("{CHUNK_ID}", cid).replace("{CHUNK}", str(i)).replace("{N_CHUNKS}", str(len(cs)))
                  .replace("{CHUNK_TEXT}", c.rstrip("\n")))
            (FREEZE / "prompts_A_v1" / f"{cid}_user.txt").write_text(ua, encoding="utf-8", newline="\n")
            (FREEZE / "prompts_B_v2" / f"{cid}_user.txt").write_text(ub, encoding="utf-8", newline="\n")
            n_chunk = tok_count(a.port, c)
            chatml = ckd_sett["local_chat_wrapper"].replace("{SYSTEM}", prompts[("extractor_A", "system_prompt")].rstrip("\n")).replace("{USER}", ua.rstrip("\n"))
            assert n_chunk <= MAX_TOK and tok_count(a.port, chatml) + N_PREDICT <= CTX, cid
            pgs = [int(x) for x in re.findall(r"=== PDF page (\d+)", c)]
            rows.append({"chunk_id": cid, "unit": u["unit"], "document": "aha_acc_2025", "chunk": i, "n_chunks": len(cs),
                         "chunk_tokens": n_chunk, "first_pdf_page": min(pgs), "last_pdf_page": max(pgs),
                         "sha256_chunk": sha256_text(c), "sha256_user_A_v1": sha256_text(ua), "sha256_user_B_v2": sha256_text(ub)})
            print(cid, n_chunk, flush=True)
    with open(FREEZE / "chunk_index.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print("units", len(units), "chunks", len(rows))


if __name__ == "__main__":
    main()
