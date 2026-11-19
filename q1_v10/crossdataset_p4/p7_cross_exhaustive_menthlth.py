"""Sensitivity (P7 journal review, round 5): MentHlth in NHIS and NHANES is a proxy with few observed codes
(NHIS DEPFREQ_A -> 0, 1, 4, 30 days; NHANES PHQ-9 bands -> 0, 5, 10, 20, 30 days), but the exhaustive search
moves it to any whole number 0-30. Restrict MentHlth candidates to the observed codes (inside the permitted
range) and rerun the exhaustive search in all three modes. Writes tag _mh_exh (picked up by p7_exh_bootstrap.py)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # v10 shadow: python -I omits the script dir
import sys

import numpy as np

import p7_cross_exhaustive as E

CODES = {"nhis": [0, 1, 4, 30], "nhanes": [0, 5, 10, 20, 30]}
ds = sys.argv[sys.argv.index("--dataset") + 1]
codes = np.array(CODES["nhis" if ds.startswith("nhis") else "nhanes"], dtype=float)
_grid = E.grid


def grid(name, cur, rng):
    if name != "MentHlth":
        return _grid(name, cur, rng)
    lo, hi = rng
    vals = codes[(codes >= np.ceil(lo)) & (codes <= np.floor(hi))]
    return vals[vals != round(cur)]


E.grid = grid
if "--tag" not in sys.argv:
    sys.argv += ["--tag", "_mh_exh"]
E.main()
