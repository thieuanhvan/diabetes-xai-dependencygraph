"""Is the checkout actually the build you think it is?

Standalone: `python analysis/check_install.py`

Extracting an archive over an existing folder is easy to skip, and a stale
checkout fails silently: the scripts run, produce numbers, and look right. This
prints the build stamp and verifies that every file the current build should
contain is present.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from depgraph.version import EXPECTED, RELEASED, REPO_VERSION
except ModuleNotFoundError:
    raise SystemExit(
        "src/depgraph/version.py is missing.\n"
        "This checkout predates v18. The archive was not extracted over it.")

print(f"repo    : {ROOT}")
print(f"build   : {REPO_VERSION}  ({RELEASED})")

missing = [f for f in EXPECTED if not (ROOT / f).exists()]
for f in EXPECTED:
    print(f"  {'ok  ' if (ROOT / f).exists() else 'MISS'}  {f}")

try:
    from depgraph.paths import find_dump, pipeline_repo, search_paths
    print(f"\npipeline repo : {pipeline_repo() or 'NOT FOUND, set PIPELINE_REPO'}")
    print("dump search order :")
    for d in search_paths():
        print(f"  {'exists ' if d.exists() else 'missing'}  {d}")
    print()
    import csv
    for name in ("raw_cf_changes.csv", "sweep_changes_seed42_published.csv"):
        p = find_dump(name, required=False)
        if p is None:
            print(f"    {name}: not found anywhere")
            continue
        # Print the row count, because that is the fastest way to see which run
        # is about to be analysed without opening the file.
        with open(p, newline="") as fh:
            n = sum(1 for _ in csv.DictReader(fh))
        print(f"      -> {n} recorded feature changes")
except Exception as exc:  # pragma: no cover
    print(f"\npath resolution unavailable: {exc}")

if missing:
    raise SystemExit(f"\n{len(missing)} file(s) missing. Extract the archive again, "
                     f"making sure it overwrites the existing folder.")
print("\nOK: this checkout is complete.")
