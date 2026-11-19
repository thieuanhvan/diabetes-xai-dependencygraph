"""Pair every number of the v9 result files with the same number of the v10 re-run (P5 frames).

For each JSON / CSV result file under outputs/ (v9) that also exists under p5_v10/outputs/ (v10), numbers are
flattened to keys (file :: json path, or file :: row key :: column) and written side by side to
numbers_v9_v10.csv. `python -I numbers_v9_v10.py find 30.29 0.7681 ...` lists the keys whose v9 value, truncated as
printed in the manuscript (4 decimals, or 2 decimals of a percentage), equals each argument, with the v10 value.
Read only outside p5_v10.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import pandas as pd

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
O9 = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs")
O10 = HERE / "outputs"
SKIP = ("_archived", "_interrupted", "p5_migration", "p5_v10", "_identity_failed")


def flat(x, pre=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from flat(v, f"{pre}/{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from flat(v, f"{pre}[{i}]")
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        yield pre, float(x)


def csv_items(p: Path):
    try:
        d = pd.read_csv(p, low_memory=False)
    except Exception:
        return {}
    if len(d) > 3000:
        return {}
    keycols = [c for c in d.columns if d[c].dtype == object][:4]
    out = {}
    for i, r in d.iterrows():
        k = "|".join(str(r[c]) for c in keycols) if keycols else str(i)
        for c in d.columns:
            v = r[c]
            if c in keycols or not isinstance(v, (int, float)) or isinstance(v, bool) or pd.isna(v):
                continue
            out[f"{k}::{c}"] = float(v)
    return out


def items(p: Path):
    if p.suffix == ".json":
        try:
            return dict(flat(json.loads(p.read_text(encoding="utf-8"))))
        except Exception:
            return {}
    return csv_items(p)


def build():
    rows = []
    for p10 in O10.rglob("*"):
        if p10.suffix not in (".json", ".csv") or not p10.is_file():
            continue
        rel = p10.relative_to(O10)
        if any(s in str(rel) for s in SKIP) or "_changes" in p10.name or "kept_" in p10.name or "out_" in p10.name:
            continue
        p9 = O9 / rel
        if not p9.exists():
            continue
        a, b = items(p9), items(p10)
        for k in a.keys() | b.keys():
            rows.append({"file": rel.as_posix(), "key": k, "v9": a.get(k), "v10": b.get(k)})
    d = pd.DataFrame(rows)
    d.to_csv(HERE / "numbers_v9_v10.csv", index=False, lineterminator="\n")
    print(len(d), "numbers in", d.file.nunique(), "files")


def trunc(x, k):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


def find(args):
    d = pd.read_csv(HERE / "numbers_v9_v10.csv")
    d = d[d.v9.notna()]
    for a in args:
        pct = a.endswith("%")
        t = float(a.rstrip("%"))
        k = len(a.rstrip("%").split(".")[1]) if "." in a else 0
        hit = d[[abs(trunc((v * 100 if pct else v), k) - t) < 1e-9 or (not pct and abs(trunc(v * 100, k) - t) < 1e-9)
                 for v in d.v9]]
        print(f"== {a}: {len(hit)} keys")
        for r in hit.head(12).itertuples():
            print(f"   {r.file} :: {r.key} :: v9 {r.v9} -> v10 {r.v10}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "find":
        find(sys.argv[2:])
    else:
        build()
