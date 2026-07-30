"""Where the counterfactual dumps live, and which copy is being read.

The runners write to ``PIPELINE_REPO/outputs_kg`` because that is where the P4
pipeline keeps its artefacts. The analysis scripts used to default to
``<this repo>/outputs``, which also contains a committed copy. When those two
diverge, an analysis script reads the committed copy, prints plausible numbers,
and gives no sign that it never saw the run that just finished. That happened.

Every reader now goes through :func:`find_dump`, which searches both locations,
takes the newer, and prints the path and its modification time so the source of
a number is visible in the log rather than assumed.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def pipeline_repo() -> Optional[Path]:
    """The P4 repository, from PIPELINE_REPO or as a sibling directory."""
    env = os.environ.get("PIPELINE_REPO")
    if env:
        p = Path(env)
        return p if p.exists() else None
    sib = REPO_ROOT.parent / "diabetes-xai-counterfactual"
    return sib if sib.exists() else None


def search_paths() -> List[Path]:
    """Candidate output directories, in the order the runners prefer."""
    out = []
    pr = pipeline_repo()
    if pr is not None:
        out.append(pr / "outputs_kg")
    out.append(REPO_ROOT / "outputs")
    return out


def write_dir() -> Path:
    """Where the runners write. Matches run_audit_dump.py and run_seed_sweep.py."""
    return search_paths()[0]


def _stamp(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


def find_dump(filename: str, *, echo: bool = True, required: bool = True) -> Optional[Path]:
    """The live copy of `filename`, with the choice announced.

    Precedence is the search order, not the modification time. The runners write
    to PIPELINE_REPO/outputs_kg; the copy under this repository is a committed
    snapshot that gets a fresh timestamp every time an archive is extracted over
    the checkout. Choosing by timestamp therefore picks the snapshot and silently
    reverts the analysis to whatever was committed, which is exactly the failure
    this function was added to prevent.

    Override with KG_OUTPUTS=/some/dir when neither default is right.

    Raises SystemExit when `required` and no copy exists, rather than letting a
    later KeyError or an empty result stand in for a missing file.
    """
    override = os.environ.get("KG_OUTPUTS")
    dirs = [Path(override)] + search_paths() if override else search_paths()
    # KG_OUTPUTS often names a directory that is already in search_paths()
    # (refresh_outputs.bat sets it to this repo's outputs\). Without this the
    # same file is announced twice, once as "reading" and once as
    # "ignoring (identical)", which reads like a real disagreement.
    _seen: set = set()
    _uniq = []
    for _d in dirs:
        _key = _d.resolve() if _d.exists() else _d
        if _key in _seen:
            continue
        _seen.add(_key)
        _uniq.append(_d)
    dirs = _uniq
    found = [d / filename for d in dirs if (d / filename).exists()]
    if not found:
        if not required:
            return None
        looked = "\n".join(f"    {d / filename}" for d in dirs)
        raise SystemExit(
            f"{filename} not found. Looked in:\n{looked}\n"
            f"Run run_audit_dump.py first, or set PIPELINE_REPO to the "
            f"diabetes-xai-counterfactual checkout.")
    chosen = found[0]
    if echo:
        print(f"    reading {chosen}   (modified {_stamp(chosen)})")
        for other in found[1:]:
            same = other.read_bytes() == chosen.read_bytes()
            if same:
                print(f"    ignoring {other}   (identical)")
                continue
            print(f"    ignoring {other}   (DIFFERENT, modified {_stamp(other)})")
            print(f"    NOTE: two copies of {filename} disagree. Using the one the "
                  f"runners write to. If the other is the one you want, "
                  f"set KG_OUTPUTS to its directory.")
    return chosen


if __name__ == "__main__":
    print(f"repo root      : {REPO_ROOT}")
    print(f"pipeline repo  : {pipeline_repo() or 'NOT FOUND'}")
    print(f"runners write  : {write_dir()}")
    print("search order   :")
    for d in search_paths():
        print(f"    {d}   {'exists' if d.exists() else 'missing'}")
