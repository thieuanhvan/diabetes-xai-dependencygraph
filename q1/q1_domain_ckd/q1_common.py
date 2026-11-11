"""Shared helpers for the P7 Q1 extension, step A0 (prereg v3, 11/11/2026 16:45).

Paths, SHA-256, truncation (never rounding, rulebook 5.5) and below-normal priority.
Run every script with `python -I` from the p7-carla312 venv.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
import sys
from pathlib import Path

PAPER7 = Path("D:/20-study/uit/research/diabetesxai/paper7")
PREREG = PAPER7 / "prereg" / "prereg_q1_extension_en_v3_20261111_1645.md"
PREREG_SHA256 = "95a83da578b975f5e578139182f51113020ff9fefcff927a037742b4a112369d"
OUT = PAPER7 / "outputs" / "q1_domain_ckd"
FREEZE = OUT / "a0_freeze"
REF_KDIGO = PAPER7 / "references" / "q1_kdigo"
REF_GATE = PAPER7 / "references" / "q1_recall_gate"
X5_SOURCES = PAPER7 / "killtest_x5" / "sources"
NHANES_P7_RAW = Path("C:/Repos/uit/nhanes-diabetes/data/raw/cdc")
NHANES_NEW_RAW = PAPER7 / "data_q1" / "nhanes_raw"
BRFSS2021_XPT = PAPER7 / "data_q1" / "brfss2021_raw" / "LLCP2021.XPT"
KDIGO_PDF_SHA256 = "b18db280f7dc889a1a99447b779c0312cd536f939a5180b38894a5d68e4410c0"
P7_REPO = Path("C:/Repos/uit/diabetes-xai-dependencygraph")
NHANES_REPO = Path("C:/Repos/uit/nhanes-diabetes")
TOOLS = Path(__file__).resolve().parent


def below_normal() -> None:
    """Machine rule (15/10/2026): heavy Python runs at below-normal priority."""
    if os.name == "nt":
        BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
        h = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.kernel32.SetPriorityClass(h, BELOW_NORMAL_PRIORITY_CLASS)
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(v, "2")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def trunc(x: float, nd: int = 4) -> str:
    """Truncate (not round) to nd decimals, as text."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "NA"
    f = 10 ** nd
    v = math.trunc(x * f) / f
    return f"{v:.{nd}f}"


def check_prereg() -> None:
    got = sha256_file(PREREG)
    if got != PREREG_SHA256:
        sys.exit(f"prereg hash mismatch: {got}")


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
