"""P7 Q1 extension B, POST-HOC analysis B-P1 (plan posthoc_b_mlp_plan_en_v1_20261112_0520.md): shared paths.

Everything produced with this folder is post hoc and exploratory (deviation log B-P1): H4 and H5 stay NOT REACHED
(event B-E2). The frozen extension B modules (b_common, b_models, b_methods, b_wachter_core, b_run_wachter,
b_analysis) are imported unchanged; only the MLP seed varies.
Run every script with `python -I` in the p7-carla312 venv; OMP_NUM_THREADS must not be set (bug B-E3).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
B = HERE.parent
sys.path.insert(0, str(B))

import b_common as C  # noqa: E402

PLAN = C.PAPER7 / "prereg" / "posthoc_b_mlp_plan_en_v1_20261112_0520.md"
PLAN_SHA256 = "8248bc4157fe219db2d725fe96f56dcd4df7c3385f26e11b004308f96145e863"
OUT = C.PAPER7 / "outputs" / "q1_ext_b_posthoc"
LABEL = "POST HOC (B-P1), exploratory; not part of H4/H5, which stay NOT REACHED (B-E2)"
FIRST_SEED, MAX_TRIED, MAX_ACCEPTED, MIN_ELIGIBLE = 43, 30, 5, 50


def check() -> None:
    """Frozen prereg and frozen post-hoc plan unchanged; OpenMP not limited (B-E3)."""
    C.check_prereg()
    h = C.sha256_file(PLAN)
    if h != PLAN_SHA256:
        sys.exit(f"post-hoc plan hash mismatch: {h}")
    if "OMP_NUM_THREADS" in os.environ:
        sys.exit("OMP_NUM_THREADS is set; unset it (bug B-E3)")


def mlp_dir(seed: int) -> Path:
    return OUT / "models" / f"mlp_s{seed}"


def wachter_dir(seed: int) -> Path:
    return OUT / f"wachter_mlp_s{seed}"
