"""Shared helpers for the P7 hypertension (HTN) domain, step A0-HTN.

Paths, SHA-256, truncation (never rounding, rulebook 5.5) and below-normal priority.
Unlike q1_domain_ckd/q1_common.py, nothing here sets OMP_NUM_THREADS or other thread variables
(machine rule of 12/11/2026, after deviation B-E3). Run every script with `python -I` from the
p7-carla312 venv. Design and data only: no model is fitted and no counterfactual is generated here.
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
PREREG_V3 = PAPER7 / "prereg" / "prereg_q1_extension_en_v3_20261111_1645.md"
PREREG_V3_SHA256 = "95a83da578b975f5e578139182f51113020ff9fefcff927a037742b4a112369d"
OUT = PAPER7 / "outputs" / "q1_domain_htn"
FREEZE = OUT / "a0_freeze"
CKD_OUT = PAPER7 / "outputs" / "q1_domain_ckd"          # read only
CKD_FREEZE = CKD_OUT / "a0_freeze"                       # read only
REF_HTN = PAPER7 / "references" / "q1_htn"
NHANES_P7_RAW = Path("C:/Repos/uit/nhanes-diabetes/data/raw/cdc")
NHANES_NEW_RAW = PAPER7 / "data_q1" / "nhanes_raw"
NHANES_REPO = Path("C:/Repos/uit/nhanes-diabetes")
P7_REPO = Path("C:/Repos/uit/diabetes-xai-dependencygraph")
TOOLS = Path(__file__).resolve().parent
CKD_TOOLS = TOOLS.parent / "q1_domain_ckd"                # read only, imported for shared helpers


def below_normal() -> None:
    """Machine rule (15/10/2026): heavy Python runs at below-normal priority. Sets no thread variables."""
    if os.name == "nt":
        BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
        h = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.kernel32.SetPriorityClass(h, BELOW_NORMAL_PRIORITY_CLASS)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def trunc(x, nd: int = 4) -> str:
    """Truncate (not round) to nd decimals, as text."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "NA"
    f = 10 ** nd
    v = math.trunc(float(x) * f) / f
    return f"{v:.{nd}f}"


def check_prereg() -> None:
    got = sha256_file(PREREG_V3)
    if got != PREREG_V3_SHA256:
        sys.exit(f"prereg v3 hash mismatch: {got}")


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
