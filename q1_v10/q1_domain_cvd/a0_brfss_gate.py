"""A0 gate checks for the expected-degenerate CVD replication on BRFSS 2021 (prereg v3 4.5).

Checks variable names (_MICHD, DIABETE4, _RFSMOK3, TOLDHI3 and the P4 feature sources) in the CDC LLCP2021.XPT
and the coverage of TOLDHI3 (share of respondents with a valid 1/2 answer). The label _MICHD is checked for
presence only; its distribution is not computed. Usage: python -I a0_brfss_gate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "q1_domain_ckd"))
from q1_common import BRFSS2021_XPT, OUT, below_normal, check_prereg, sha256_file, trunc, write_json  # noqa: E402

NEEDED = ["_MICHD", "DIABETE4", "_RFSMOK3", "TOLDHI3", "_RFHYPE6", "_BMI5", "SMOKE100", "CVDSTRK3", "_TOTINDA",
          "_FRTLT1A", "_VEGLT1A", "_RFDRHV7", "_HLTHPLN", "MEDCOST1", "GENHLTH", "MENTHLTH", "PHYSHLTH", "DIFFWALK",
          "_SEX", "_AGEG5YR", "EDUCA", "INCOME3", "_CHOLCH3"]


def main():
    below_normal()
    check_prereg()
    n = 0
    cols = None
    valid = {"TOLDHI3": 0, "_RFSMOK3": 0, "DIABETE4": 0}
    nonmissing_michd = 0
    for ch in pd.read_sas(BRFSS2021_XPT, format="xport", encoding="latin-1", chunksize=50000):
        if cols is None:
            cols = list(ch.columns)
            missing = [c for c in NEEDED if c not in cols]
            if missing:
                print("missing names:", missing)
        n += len(ch)
        if "TOLDHI3" in ch:
            valid["TOLDHI3"] += int(ch["TOLDHI3"].isin([1, 2]).sum())
        if "_RFSMOK3" in ch:
            valid["_RFSMOK3"] += int(ch["_RFSMOK3"].isin([1, 2]).sum())
        if "DIABETE4" in ch:
            valid["DIABETE4"] += int(ch["DIABETE4"].isin([1, 2, 3, 4]).sum())
        if "_MICHD" in ch:
            nonmissing_michd += int(ch["_MICHD"].notna().sum())
    res = {"file": str(BRFSS2021_XPT), "sha256": sha256_file(BRFSS2021_XPT), "n_records": n,
           "names_present": {c: c in cols for c in NEEDED},
           "valid_answer_share_truncated": {k: trunc(v / n) for k, v in valid.items()},
           "valid_answer_counts": valid, "_MICHD_nonmissing_count": nonmissing_michd,
           "note": "_MICHD distribution not computed (label of the replication)."}
    write_json(OUT.parent / "q1_domain_cvd" / "a0_gate_brfss2021.json", res)
    print(res)


if __name__ == "__main__":
    main()
