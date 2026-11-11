"""Append superseding entries to the A0 manifest after a logged fix, without rewriting earlier lines.

Earlier lines whose path matches a superseded file get the suffix "  [SUPERSEDED <tag>]"; the new hashes are
appended in a dated block; the manifest's new hash is appended to prereg/MANIFEST_sha256.txt.
Usage: python -I a0_manifest_append.py <tag> <reason> <file> [<file> ...]
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from q1_common import FREEZE, PAPER7, check_prereg, sha256_file


def main():
    check_prereg()
    tag, reason, files = sys.argv[1], sys.argv[2], [Path(f) for f in sys.argv[3:]]
    man = FREEZE / "A0_MANIFEST_sha256.txt"
    rels = {p.relative_to(PAPER7).as_posix() if p.is_relative_to(PAPER7) else p.as_posix(): p for p in files}
    out = []
    for line in man.read_text(encoding="utf-8").splitlines():
        parts = line.split(" *", 1)
        if len(parts) == 2 and parts[1].strip() in rels and "[SUPERSEDED" not in line:
            line += f"  [SUPERSEDED {tag}]"
        out.append(line)
    out += ["", f"## {tag} ({datetime.now():%d/%m/%Y %H:%M}): {reason}"]
    out += [f"{sha256_file(p)} *{r}" for r, p in rels.items()]
    man.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    h = sha256_file(man)
    pm = PAPER7 / "prereg" / "MANIFEST_sha256.txt"
    pm.write_text(pm.read_text(encoding="utf-8").rstrip("\n") + "\n"
                  + f"{h} *../outputs/q1_domain_ckd/a0_freeze/A0_MANIFEST_sha256.txt (A0 manifest after {tag})\n",
                  encoding="utf-8", newline="\n")
    print(man, h)


if __name__ == "__main__":
    main()
