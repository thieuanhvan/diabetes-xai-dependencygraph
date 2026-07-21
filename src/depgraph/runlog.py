"""Timing and environment logging.

Every run_*.py and analysis/*.py step is wrapped so the console shows how long
each stage took, and so the environment that produced a number is recorded next
to it. Counterfactual generation is the slow stage and the one whose exact
output depends on library versions, so both matter.

Usage:
    from depgraph.runlog import RunLog
    log = RunLog("run_seed_sweep")
    with log.step("load BRFSS"):
        ...
    log.finish(out_dir)          # writes <name>_runlog.json next to the outputs
"""
from __future__ import annotations

import json
import platform
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from depgraph.version import RELEASED, REPO_VERSION


# import name -> distribution name on PyPI, where they differ
_DISTS = {"sklearn": "scikit-learn", "dice_ml": "dice-ml"}


def _version(mod: str) -> str:
    """Version of an installed package.

    A module can be importable and still have no __version__ attribute, which is
    exactly the case for dice_ml. Asking the package metadata first avoids
    reporting an installed library as missing, and the two states are kept
    distinct: "installed, version unknown" is not "not installed".
    """
    from importlib import metadata
    for dist in (_DISTS.get(mod, mod), mod, mod.replace("_", "-")):
        try:
            return metadata.version(dist)
        except Exception:
            pass
    try:
        m = __import__(mod)
    except Exception:
        return "not installed"
    return str(getattr(m, "__version__", "installed, version unknown"))


def environment() -> Dict[str, str]:
    """Versions of everything that can change a counterfactual."""
    env = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "repo_version": REPO_VERSION,
    }
    for mod in ("numpy", "pandas", "sklearn", "xgboost", "dice_ml", "scipy"):
        env[mod] = _version(mod)
    return env


class RunLog:
    def __init__(self, name: str, echo: bool = True):
        self.name = name
        self.echo = echo
        self.started = time.time()
        self.started_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        self.steps: List[Dict] = []
        self.env = environment()
        if echo:
            print(f"[{name}] repo {REPO_VERSION} ({RELEASED})   start {self.started_iso}")
            print(f"[{name}] python {self.env['python']}  numpy {self.env['numpy']}  "
                  f"xgboost {self.env['xgboost']}  dice_ml {self.env['dice_ml']}")

    @contextmanager
    def step(self, label: str):
        t0 = time.time()
        if self.echo:
            print(f"[{self.name}] -> {label} ...", flush=True)
        try:
            yield
        finally:
            dt = time.time() - t0
            self.steps.append({"label": label, "seconds": round(dt, 2)})
            if self.echo:
                print(f"[{self.name}] <- {label}  {dt:8.2f}s", flush=True)

    def mark(self, label: str, seconds: float) -> None:
        """Record a stage that was timed by hand."""
        self.steps.append({"label": label, "seconds": round(seconds, 2)})

    def finish(self, out_dir: Path | None = None) -> Dict:
        total = time.time() - self.started
        payload = {
            "run": self.name,
            "started": self.started_iso,
            "total_seconds": round(total, 2),
            "steps": self.steps,
            "environment": self.env,
        }
        if self.echo:
            print(f"\n[{self.name}] timing")
            width = max((len(s["label"]) for s in self.steps), default=10)
            for s in self.steps:
                print(f"    {s['label']:<{width}}  {s['seconds']:9.2f}s")
            print(f"    {'TOTAL':<{width}}  {total:9.2f}s")
        if out_dir is not None:
            out_dir = Path(out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"{self.name}_runlog.json"
            path.write_text(json.dumps(payload, indent=2))
            if self.echo:
                print(f"-> {path}")
        return payload


if __name__ == "__main__":
    log = RunLog("runlog_selftest")
    with log.step("sleep a little"):
        time.sleep(0.2)
    with log.step("sleep a little more"):
        time.sleep(0.1)
    log.finish()
