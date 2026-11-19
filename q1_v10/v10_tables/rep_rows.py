"""rep_rows.py <md file> <rows file> <first-row prefix> <count>: replace <count> table rows starting at the unique line
that begins with <first-row prefix> by the rows in <rows file>."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
md, rows, prefix, cnt = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], int(sys.argv[4])
lines = md.read_text(encoding="utf-8").split("\n")
hit = [k for k, l in enumerate(lines) if l.startswith(prefix)]
assert len(hit) == 1, (prefix, len(hit))
new = rows.read_text(encoding="utf-8").strip().split("\n")
assert len(new) == cnt and all(l.startswith("|") for l in lines[hit[0]:hit[0] + cnt])
lines[hit[0]:hit[0] + cnt] = new
md.write_text("\n".join(lines), encoding="utf-8")
print("replaced", cnt, "rows at line", hit[0] + 1)
