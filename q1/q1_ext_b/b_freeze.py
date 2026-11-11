"""Freeze extension B into the A0 manifest before any real-data run (prereg v3 5.4 step 1, 9 "Script hashing"),
in the same way as the A2-freeze block: one dated block of SHA-256 lines appended to
outputs/q1_domain_ckd/a0_freeze/A0_MANIFEST_sha256.txt (earlier lines untouched; reused files that are already in
the manifest with the same hash are hashed again, not marked superseded), and the manifest's new hash appended to
prereg/MANIFEST_sha256.txt.
Usage: python -I b_freeze.py <tag> <reason>      (refuses if test_b_results.json is missing or not all-pass)
       python -I b_freeze.py --verify <tag>       (re-hash every file of block <tag>; exit 1 on any mismatch)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b_common as C  # noqa: E402
import b_vendor as V  # noqa: E402

MAN = C.PAPER7 / "outputs" / "q1_domain_ckd" / "a0_freeze" / "A0_MANIFEST_sha256.txt"
PM = C.PAPER7 / "prereg" / "MANIFEST_sha256.txt"
DG = Path("C:/Repos/uit/diabetes-xai-dependencygraph/src/depgraph")


def files():
    out = sorted(p for p in HERE.glob("*.py"))
    out += [V.VENDOR / r for r in V.FILES]
    out += [HERE.parent / "crossdataset_p4" / "p7_cross_p4pipeline.py",
            HERE.parent / "crossdataset_p4" / "p7_cross_exhaustive.py",
            HERE.parent / "q1_domain_ckd" / "a2_domain.py",
            DG / "nodes.py", DG / "edges.py", DG / "audit.py",
            C.OUT / "unit_tests" / "test_b_results.json", C.OUT / "unit_tests" / "brfss_t2d_graph.ttl"]
    return out


def rel(p: Path) -> str:
    return p.relative_to(C.PAPER7).as_posix() if p.is_relative_to(C.PAPER7) else p.as_posix()


def main():
    C.check_prereg()
    if sys.argv[1] == "--verify":
        tag = sys.argv[2]
        lines = MAN.read_text(encoding="utf-8").splitlines()
        start = next(i for i, l in enumerate(lines) if l.startswith(f"## {tag} "))
        bad = 0
        for l in lines[start + 1:]:
            if l.startswith("## ") or not l.strip():
                break
            h, r = l.split(" *", 1)
            p = Path(r) if Path(r).is_absolute() else C.PAPER7 / r
            if C.sha256_file(p) != h:
                print("MISMATCH", r)
                bad += 1
        print(f"{tag}: {bad} mismatches")
        sys.exit(1 if bad else 0)
    tag, reason = sys.argv[1], sys.argv[2]
    tr = json.loads((C.OUT / "unit_tests" / "test_b_results.json").read_text(encoding="utf-8"))
    if not tr.get("all_pass"):
        sys.exit("unit tests not all passing; no freeze")
    V.verify()
    block = ["", f"## {tag} ({datetime.now():%d/%m/%Y %H:%M}): {reason}"]
    block += [f"{C.sha256_file(p)} *{rel(p)}" for p in files()]
    text = MAN.read_text(encoding="utf-8").rstrip("\n") + "\n" + "\n".join(block) + "\n"
    MAN.write_text(text, encoding="utf-8", newline="\n")
    h = C.sha256_file(MAN)
    PM.write_text(PM.read_text(encoding="utf-8").rstrip("\n") + "\n"
                  + f"{h} *../outputs/q1_domain_ckd/a0_freeze/A0_MANIFEST_sha256.txt (A0 manifest after {tag})\n",
                  encoding="utf-8", newline="\n")
    print(MAN, h, len(block) - 2, "files")


if __name__ == "__main__":
    main()
