"""A0: text conversions, extraction units, chunks and rendered prompts (prereg v3 4.3-4.4).

Needs a llama.cpp b12283 llama-server with the Qwen2.5-7B GGUF on --port (tokenizer only; no generation).
Writes under outputs/q1_domain_ckd/a0_freeze/:
  (pdftotext -raw and -layout of every source are written next to the PDF under paper7/references/)
  units/     one page-marked text file per extraction unit
  chunks/    chunk files (identical for both extractors)
  prompts/   user message per chunk (both extractors) and full ChatML prompt per chunk (local model)
  chunk_index.csv
Usage: python -I a0_build_chunks.py --port 8089
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

from q1_common import (FREEZE, KDIGO_PDF_SHA256, REF_GATE, REF_KDIGO, TOOLS, X5_SOURCES, below_normal,
                       check_prereg, sha256_file, sha256_text, write_json)

MAX_TOK, OVERLAP = 6000, 500
CTX, N_PREDICT = 16384, 2048


def tok_count(port: int, text: str) -> int:
    req = urllib.request.Request(f"http://127.0.0.1:{port}/tokenize",
                                 data=json.dumps({"content": text, "add_special": False}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return len(json.loads(r.read())["tokens"])


def pdftotext(pdf: Path, out_dir: Path, stem: str) -> dict:
    res = {}
    for mode in ("raw", "layout"):
        out = out_dir / f"{stem}_{mode}.txt"
        subprocess.run(["pdftotext", f"-{mode}", "-enc", "UTF-8", str(pdf), str(out)], check=True)
        res[mode] = out
    return res


def pages_of(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\f")


def marked(lines_by_page: list[tuple[int, list[str]]]) -> str:
    out = []
    for pg, lines in lines_by_page:
        if not lines:
            continue
        out.append(f"=== PDF page {pg} ===")
        out.extend(lines)
    return "\n".join(out).strip() + "\n"


def kdigo_units(raw_pages, layout_pages, spec) -> dict[str, str]:
    foot = [re.compile(p) for p in spec["footer_patterns"]]
    flat = []  # (page, line)
    for i, p in enumerate(raw_pages, 1):
        if i < spec["min_pdf_page"]:
            continue
        for ln in p.splitlines():
            s = ln.rstrip()
            if any(f.match(s.strip()) for f in foot):
                continue
            flat.append((i, s))

    def find(rx, start=0):
        r = re.compile(rx)
        for k in range(start, len(flat)):
            if r.match(flat[k][1].strip()):
                return k
        raise ValueError(f"anchor not found: {rx}")

    def block(rx_s, rx_e, lo, hi):
        s = find(rx_s, lo)
        e = find(rx_e, s)
        assert lo <= s <= e < hi, (rx_s, s, e, lo, hi)
        return s, e + 1

    units = {}
    spans = {}
    for u in spec["section_units"]:
        s = find(u["start"])
        e = find(u["end"], s + 1)
        spans[u["unit"]] = (s, e)
    for u in spec["section_units"]:
        s, e = spans[u["unit"]]
        idx = list(range(s, e))
        if "remove_block" in u:
            bs, be = block(u["remove_block"]["start"], u["remove_block"]["end_inclusive"], s, e)
            idx = [k for k in idx if not (bs <= k < be)]
        if "append_block" in u:
            nxt = [v for v in spec["section_units"] if v["unit"] != u["unit"] and spans[v["unit"]][0] == e][0]
            ns, ne = spans[nxt["unit"]]
            bs, be = block(u["append_block"]["start"], u["append_block"]["end_inclusive"], ns, ne)
            idx += list(range(bs, be))
        by_page: list[tuple[int, list[str]]] = []
        for k in idx:
            pg, ln = flat[k]
            if not by_page or by_page[-1][0] != pg:
                by_page.append((pg, []))
            by_page[-1][1].append(ln)
        units[u["unit"]] = marked(by_page)
    for t in spec["table_units"]:
        by_page = []
        for b in t["blocks"]:
            lines = layout_pages[b["pdf_page"] - 1].splitlines()
            rs, re_ = re.compile(b["start"]), re.compile(b["end"])
            s = next(k for k, l in enumerate(lines) if rs.match(l))
            e = next(k for k in range(s + 1, len(lines)) if re_.match(lines[k]))
            by_page.append((b["pdf_page"], [l.rstrip() for l in lines[s:e]]))
        units[t["unit"]] = marked(by_page)
    return units


def whole_doc(raw_pages) -> str:
    return marked([(i, [l.rstrip() for l in p.splitlines()]) for i, p in enumerate(raw_pages, 1)])


def chunk(port: int, text: str) -> list[str]:
    lines = text.split("\n")
    counts = [tok_count(port, l + "\n") for l in lines]
    if sum(counts) <= MAX_TOK and tok_count(port, text) <= MAX_TOK:
        return [text]
    chunks, start = [], 0
    while start < len(lines):
        end, tot = start, 0
        while end < len(lines) and tot + counts[end] <= MAX_TOK - 50:  # 50-token margin for merge effects
            tot += counts[end]
            end += 1
        if end == start:
            raise ValueError("single line longer than the chunk limit")
        piece = "\n".join(lines[start:end]).strip("\n") + "\n"
        assert tok_count(port, piece) <= MAX_TOK
        # carry the page marker into a chunk that starts mid-page
        if not lines[start].startswith("=== PDF page"):
            prev = next((lines[k] for k in range(start, -1, -1) if lines[k].startswith("=== PDF page")), None)
            if prev:
                piece = f"{prev} (continued)\n" + piece
        chunks.append(piece)
        if end >= len(lines):
            break
        # next start: last line break at or before end - OVERLAP tokens
        acc, nxt = 0, end
        while nxt > start and acc < OVERLAP:
            nxt -= 1
            acc += counts[nxt]
        start = max(nxt, start + 1)
    return chunks


def main():
    below_normal()
    check_prereg()
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8089)
    a = ap.parse_args()
    spec = json.loads((TOOLS / "section_list_v1.json").read_text(encoding="utf-8"))
    sett = json.loads((TOOLS / "extraction_settings_v1.json").read_text(encoding="utf-8"))
    system = (TOOLS / sett["prompt_files"]["system"]).read_text(encoding="utf-8")
    user_t = (TOOLS / sett["prompt_files"]["user_template"]).read_text(encoding="utf-8")
    for d in ("units", "chunks", "prompts", "sources"):
        (FREEZE / d).mkdir(parents=True, exist_ok=True)

    kpdf = REF_KDIGO / spec["kdigo"]["pdf"]
    assert sha256_file(kpdf) == KDIGO_PDF_SHA256, "KDIGO PDF differs from the pre-plan copy"
    REF_GATE.mkdir(parents=True, exist_ok=True)
    srcs = {"kdigo": kpdf}
    for d in spec["recall_gate"]["documents"]:
        dst = REF_GATE / d["pdf"]
        if not dst.exists():
            shutil.copy2(X5_SOURCES / d["pdf"], dst)
        assert sha256_file(dst) == sha256_file(X5_SOURCES / d["pdf"])
        srcs[d["unit"]] = dst
    ver = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True).stderr.splitlines()[0]

    texts = {k: pdftotext(p, p.parent, p.stem) for k, p in srcs.items()}  # prereg 10: under references/
    units = kdigo_units(pages_of(texts["kdigo"]["raw"]), pages_of(texts["kdigo"]["layout"]), spec["kdigo"])
    labels = {u["unit"]: u["label"] for u in spec["kdigo"]["section_units"] + spec["kdigo"]["table_units"]}
    doc_of = {u: "kdigo" for u in units}
    for d in spec["recall_gate"]["documents"]:
        units[d["unit"]] = whole_doc(pages_of(texts[d["unit"]]["raw"]))
        labels[d["unit"]] = d["label"] + " (whole document)"
        doc_of[d["unit"]] = d["unit"]
    doc_label = {"kdigo": "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease"}
    doc_label.update({d["unit"]: d["label"] for d in spec["recall_gate"]["documents"]})

    rows = []
    for u, txt in units.items():
        (FREEZE / "units" / f"{u}.txt").write_text(txt, encoding="utf-8", newline="\n")
        cs = chunk(a.port, txt)
        for i, c in enumerate(cs, 1):
            cid = f"{u}_c{i:02d}"
            (FREEZE / "chunks" / f"{cid}.txt").write_text(c, encoding="utf-8", newline="\n")
            user = (user_t.replace("{DOCUMENT_LABEL}", doc_label[doc_of[u]])
                    .replace("{LICENCE_NOTICE}", sett["licence_notices"][doc_of[u]])
                    .replace("{UNIT_LABEL}", labels[u]).replace("{CHUNK_INDEX}", str(i))
                    .replace("{CHUNK_COUNT}", str(len(cs))).replace("{CHUNK_TEXT}", c.rstrip("\n")))
            full = sett["local_chat_wrapper"].replace("{SYSTEM}", system.rstrip("\n")).replace("{USER}", user.rstrip("\n"))
            (FREEZE / "prompts" / f"{cid}_user.txt").write_text(user, encoding="utf-8", newline="\n")
            (FREEZE / "prompts" / f"{cid}_chatml.txt").write_text(full, encoding="utf-8", newline="\n")
            n_chunk, n_full = tok_count(a.port, c), tok_count(a.port, full)
            assert n_chunk <= MAX_TOK and n_full + N_PREDICT <= CTX, (cid, n_chunk, n_full)
            pgs = [int(x) for x in re.findall(r"=== PDF page (\d+)", c)]
            rows.append({"chunk_id": cid, "unit": u, "document": doc_of[u], "chunk": i, "n_chunks": len(cs),
                         "chunk_tokens": n_chunk, "prompt_tokens": n_full, "first_pdf_page": min(pgs), "last_pdf_page": max(pgs),
                         "sha256_chunk": sha256_text(c), "sha256_user": sha256_text(user), "sha256_chatml": sha256_text(full)})
            print(cid, n_chunk, n_full, flush=True)
    with open(FREEZE / "chunk_index.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    write_json(FREEZE / "sources" / "sources.json", {
        "pdftotext": ver, "sources": {k: {"pdf": str(p), "sha256": sha256_file(p),
                                          "raw_txt_sha256": sha256_file(texts[k]["raw"]),
                                          "layout_txt_sha256": sha256_file(texts[k]["layout"])} for k, p in srcs.items()}})
    print("units", len(units), "chunks", len(rows))


if __name__ == "__main__":
    main()
