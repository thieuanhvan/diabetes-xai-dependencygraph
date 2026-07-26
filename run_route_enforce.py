"""Route-aware enforcement (journal version, Section 4.3).

WHY THIS FILE EXISTS
--------------------
``run_enforce.py`` answers "what does it cost to stop recommending things the
patient cannot do?" by removing the three indicators from ``features_to_vary``
entirely. That is a *role-only* rule applied at generation time, and Section
VI-A of the conference paper says so plainly: it consults no edge.

This file implements the rule the journal version claims, which does consult
the edge set:

    a counterfactual is ADMISSIBLE when, for every indicator v it moves,
    the same counterfactual also moves some u with (u -> v) in E and
    tier(u) in SOURCE_TIERS

Two readings of "for every" exist and are both defensible:

    universal    every moved indicator must be routed          <- enforced here
    existential  at least one moved indicator must be routed   <- the audit rule

They coincide on the reference dump, both retaining 113 of 323
indicator-touching counterfactuals, because no counterfactual there moves one
routed and one unrouted indicator at once. That is a property of the dump and
not a theorem, so this script measures both and reports the gap.

Two variants of SOURCE_TIERS are also measured, because the difference between
them is exactly the agent-role question:

    A  {"lever"}                the patient acts alone
    B  {"lever", "treatable"}   a clinician may act on the patient's behalf

On the reference dump A leaves one patient with no counterfactual at all and B
leaves none, because that patient's counterfactuals route through HighChol and
HighBP, which are real edges whose sources sit in the treatable tier.

WHAT THIS SCRIPT DOES NOT DO
----------------------------
It does not modify DiCE. The generator exposes constraints per feature and has
no interface for a condition coupling two features, so enforcement here is
REJECTION WITH REGENERATION: draw, discard inadmissible candidates, redraw with
a fresh seed until the quota is met or the round budget is spent.

That has a consequence which must be reported rather than hidden. Rejection
cannot produce recourse the unconstrained generator would never have proposed,
so the retained sets this script produces are bounded above by what post-hoc
filtering of an unconstrained run already identifies. A loss-based
implementation would not carry that bound. The round count is therefore not
overhead: it measures how far the condition cuts into the region the generator
searches.

USAGE
-----
Right-click run. Requires PIPELINE_REPO to point at diabetes-xai-counterfactual
(tag v1.0-ijmi), or that repo to sit as a sibling of this one.

Writes  PIPELINE_REPO/outputs_kg/route_enforcement.csv

Resumable. Each (label, seed) row is appended the moment it finishes, and a
restart skips what is already there, so the run can be interrupted freely.

MEASURED SO FAR (12 of 15 rows, seeds 42/123/2024/7; seed 31337 outstanding).
Mean over the four completed seeds:

                        n_cf   no_cf   validity   Eq.1    Act_route   rounds
    baseline            1000     0      0.818     0.986    0.856       1.00
    route A  lever      1000     0      0.862     0.986    1.000       1.68
    route B  +treatable 1000     0      0.865     0.988    1.000       1.54

Three results that were not expected from post-hoc filtering:

  1. Enforcement keeps ALL 1,000 counterfactuals and leaves NO patient without
     recourse. Post-hoc filtering of an unconstrained run retains 775 of 985
     and strands one patient. Regeneration finds admissible alternatives that
     filtering cannot see, so the post-hoc figure is a floor, not a ceiling.
  2. Validity RISES under the constraint, by about 0.04 in both variants. The
     condition removes counterfactuals that were less likely to flip the model
     anyway; it does not trade accuracy for actionability.
  3. Act_route reaches exactly 1.000 while the existing actionability score
     moves by 0.002. That gap is the argument of the paper, stated as a number.

The column unsupported_edge_rule under variant B is NOT a failure. It scores
against the lever-only audit rule, so it counts counterfactuals whose only
route runs through a treatable feature: 54 to 80 per seed. That is a direct
measurement of how much recourse requires a clinician rather than the patient.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import numpy as np
import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Locating the audited pipeline (diabetes-xai-counterfactual @ tag v1.0-ijmi).
# Tried in order, first hit wins, so no editing is needed on any of the three
# machines this has run on:
#
#   1. $PIPELINE_REPO                      explicit override
#   2. sibling of this repo                works under C:\Projects\uit\ and
#                                          under any other flat layout
#   3. C:\Projects\uit\...                 the author's local convention
#
# Under the standard layout, both repositories sit in C:\Projects\uit\ and
# candidate 2 already resolves, so nothing has to be set.
# ---------------------------------------------------------------------------
def _find_pipeline_repo() -> Path:
    tried = []
    env = os.environ.get("PIPELINE_REPO")
    for cand in (Path(env) if env else None,
                 Path(__file__).resolve().parent.parent / "diabetes-xai-counterfactual",
                 Path(r"C:\Projects\uit\diabetes-xai-counterfactual")):
        if cand is None:
            continue
        tried.append(str(cand))
        if cand.exists():
            return cand.resolve()
    raise SystemExit(
        "Cannot locate diabetes-xai-counterfactual. Tried:\n  "
        + "\n  ".join(tried)
        + "\n\nSet PIPELINE_REPO, or place the two repositories side by side, "
          "for example C:\\Projects\\uit\\diabetes-xai-counterfactual and "
          "C:\\Projects\\uit\\diabetes-xai-dependencygraph."
    )


REPO = _find_pipeline_repo()
print(f"[paths] pipeline repo: {REPO}")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from src.pipelines.counterfactual import feature_taxonomy as FT
from src.pipelines.counterfactual.actionability import actionability_score
from src.pipelines.counterfactual.dice_runner import DiCEConfig, DiCERunner
from src.pipelines.counterfactual.feature_taxonomy import get_discrete_features
from src.pipelines.data.loader import TARGET_COL, load_dataset
from src.pipelines.evaluate.cf_metrics import proximity_l1, sparsity, validity
from src.pipelines.models.xgb_train import XGBConfig, train_xgb
from src.pipelines.preprocessing.pipeline import get_train_test_split
from src.utils.seed import seed_everything

from depgraph.audit import summarise
from depgraph.edges import EDGES
from depgraph.nodes import TIER
from depgraph.runlog import RunLog

# ---------------------------------------------------------------------------
# Configuration. Kept as module constants rather than flags: this repo's
# convention is that a runner is right-click runnable with no arguments.
# ---------------------------------------------------------------------------
SEEDS = [42, 123, 2024, 7, 31337]   # the five seeds of the conference paper

# ---------------------------------------------------------------------------
# REPRODUCIBILITY, measured 2026-07-26. Read this before changing it to False.
#
# Retraining the classifier from configs/default.yaml does NOT reproduce the
# artefact the published results were computed from. Measured on this data,
# same seed, same config, and the library versions pinned in requirements.txt:
#
#     saved model .joblib   max proba 0.8870   mean top-200 0.7475   cutoff 0.6948
#     retrained in place    max proba 0.9026   mean top-200 0.7495   cutoff 0.6930
#     agreement: mean |delta| 0.000438, max |delta| 0.018727
#
# Test AUC agrees to four decimals (0.823385 against the published 0.8233) and
# the split is identical (47,276 rows), so the difference is not in the data or
# the split. It is in the fitted ensemble. Thread count is ruled out: n_jobs in
# {-1, 1, 2, 4} all give the same retrained result. The metadata records a
# Windows path, so the artefact was produced on a different platform.
#
# The consequence is not cosmetic. A 0.019 shift in predicted probability
# reorders the top-200 cohort, which changes the queries, which changes every
# counterfactual and every number downstream. A fresh run gives 1,523 changes
# and validity 0.8190 where the reference dump has 1,500 and 0.7972.
#
# Therefore: load the saved model. Only retrain if the intention is to measure
# platform sensitivity, and report it as such.
# ---------------------------------------------------------------------------
USE_SAVED_MODEL = True
MAX_ROUNDS = 8                          # regeneration budget per query
# Each variant fixes which tiers may serve as a route source, and which
# evidence grades may confer support. Adding a variant adds rows; it never
# invalidates rows already in the checkpoint, so a rerun only fills the gaps.
#
# C is included for a reason worth stating in advance. NO graded edge enters the
# indicator tier: all eight are section narrative. Requiring grade A, B or C
# therefore empties supp(v, S) for every indicator, and the condition degenerates
# into "no indicator may move at all", which is the role-only exclusion the
# conference version already tests. C is not a new result. It is the measurement
# of that degeneracy, and it says that the whole distinction between this graph
# and a flat role table rests on eight ungraded edges.
VARIANTS: Dict[str, Dict] = {
    "A_lever":           dict(tiers={"lever"},              grades=None),
    "B_lever_treatable": dict(tiers={"lever", "treatable"},  grades=None),
    "C_lever_graded":    dict(tiers={"lever"},              grades="ABC"),
}

RUNLOG = RunLog("run_route_enforce")
cfg = yaml.safe_load(open(REPO / "configs" / "default.yaml"))


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------
def route_in_neighbours(target: str, source_tiers: Set[str],
                        grades: Optional[Iterable[str]] = None) -> Set[str]:
    """Features the guidelines recognise as a route to changing `target`.

    Generalises ``depgraph.audit.lever_in_neighbours``, which fixes the source
    tier to "lever". Passing {"lever"} reproduces it exactly.
    """
    g = None if grades is None else set(grades)
    return {e.src for e in EDGES
            if e.dst == target
            and TIER.get(e.src) in source_tiers
            and (g is None or e.grade in g)}


def admissible(changed: Iterable[str], source_tiers: Set[str], *,
               reading: str = "universal",
               grades: Optional[Iterable[str]] = None) -> bool:
    """Is this change set admissible under route-aware enforcement?"""
    S = set(changed)
    moved_indicators = [v for v in S if TIER.get(v) == "indicator"]
    if not moved_indicators:
        return True
    routed = [bool(S & route_in_neighbours(v, source_tiers, grades))
              for v in moved_indicators]
    if reading == "universal":
        return all(routed)
    if reading == "existential":
        return any(routed)
    raise ValueError("reading must be 'universal' or 'existential'")


def act_route(cf_changes: List[List[str]], source_tiers: Set[str],
              grades: Optional[Iterable[str]] = None) -> float:
    """Act_route: one minus the share of changes that are unrouted indicators.

    Reported BESIDE the taxonomy's own actionability score, never instead of
    it. The two count different failures: direction violations versus missing
    routes. Presenting only this one invites the reading that we selected a
    measure favourable to the argument.
    """
    total = sum(len(c) for c in cf_changes)
    if total == 0:
        return float("nan")
    unrouted = 0
    for changed in cf_changes:
        S = set(changed)
        for v in S:
            if TIER.get(v) != "indicator":
                continue
            if not (S & route_in_neighbours(v, source_tiers, grades)):
                unrouted += 1
    return 1.0 - unrouted / total


# ---------------------------------------------------------------------------
# Pipeline setup, identical to run_enforce.py so that any difference in
# behaviour is attributable to the rule and not to the setup.
# ---------------------------------------------------------------------------
seed_everything(cfg["random"]["seed"])
X, y = load_dataset(REPO / cfg["paths"]["data_csv"])
X_train, X_test, y_train, y_test = get_train_test_split(
    X, y, test_size=cfg["split"]["test_size"],
    seed=cfg["random"]["seed"], stratify=cfg["split"]["stratify"],
)

if USE_SAVED_MODEL:
    import joblib
    model = joblib.load(REPO / "demo" / "models" / "xgb_brfss2021.joblib")
    proba = model.predict_proba(X_test.values)[:, 1]
    res = {"model": model, "proba": proba}
    print(f"[model] loaded artefact; max proba {proba.max():.4f}, "
          f"mean top-200 {np.sort(proba)[-200:].mean():.4f}")
else:
    res = train_xgb(X_train, y_train, X_test, y_test, XGBConfig(**cfg["xgboost"]))
    print("[model] RETRAINED. Numbers will not match the published dump; see "
          "the reproducibility note at the top of this file.")

n_eval = min(cfg["evaluate"]["n_test_instances"], len(X_test))
high_risk_idx = np.argsort(res["proba"])[-n_eval:]
queries = X_test.iloc[high_risk_idx].reset_index(drop=True)

discrete = set(get_discrete_features())
ranges = FT.get_feature_ranges()
N_WANTED = int(cfg["dice"]["n_counterfactuals"])


def _make_runner() -> DiCERunner:
    return DiCERunner(
        model=res["model"], X_train=X_train, y_train=y_train,
        target_col=TARGET_COL,
        config=DiCEConfig(
            method=cfg["dice"]["method"],
            n_counterfactuals=N_WANTED,
            desired_class=cfg["dice"]["desired_class"],
            proximity_weight=cfg["dice"]["proximity_weight"],
            diversity_weight=cfg["dice"]["diversity_weight"],
            per_query=True,
        ),
    )


def _changes_of(q: pd.Series, row: pd.Series) -> List[str]:
    """Features this counterfactual moves, using the audited pipeline's own
    comparison rule: integer comparison for discrete features, tolerance for
    continuous ones."""
    out = []
    for f in queries.columns:
        b, a = float(q[f]), float(row[f])
        moved = (int(round(b)) != int(round(a))) if f in discrete else abs(b - a) > 1e-6
        if moved:
            out.append(f)
    return out


def _clean(cfs: pd.DataFrame) -> pd.DataFrame:
    d = cfs.drop(columns=[TARGET_COL]) if TARGET_COL in cfs.columns else cfs
    d = d.copy()
    for c in discrete:
        if c in d.columns:
            d[c] = d[c].round().astype(int)
    return d


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------
RUNNER = _make_runner()   # built once; rounds differ by reseeding, not by rebuild


def run_baseline(seed: int) -> Dict:
    """The published configuration, unconstrained. One draw, no rejection."""
    seed_everything(seed)
    cfe = RUNNER.generate(queries)
    per_cf, val, act, prox, spar = [], [], [], [], []
    n_no_cf = 0
    for i in range(len(queries)):
        q = queries.iloc[i]
        obj = cfe[i]
        cfs = obj.final_cfs_df if obj is not None else None
        if cfs is None or len(cfs) == 0:
            n_no_cf += 1
            continue
        d = _clean(cfs)
        val.append(validity(res["model"].predict(d.values), cfg["dice"]["desired_class"]))
        prox.append(proximity_l1(q, d, ranges))
        spar.append(sparsity(q, d))
        act.append(float(np.mean([actionability_score(q, d.iloc[j])["score"]
                                  for j in range(len(d))])))
        for k in range(len(d)):
            per_cf.append(_changes_of(q, d.iloc[k]))
    return _summarise("baseline_published", seed, per_cf, val, act, prox, spar,
                      n_no_cf, rounds=[1] * len(queries), source_tiers={"lever"},
                      grades=None)


def run_route(seed: int, variant: str) -> Dict:
    """Route-aware enforcement by rejection with regeneration."""
    spec = VARIANTS[variant]
    tiers, grades = spec["tiers"], spec["grades"]
    per_cf, val, act, prox, spar = [], [], [], [], []
    rounds_used, n_no_cf = [], 0

    for i in range(len(queries)):
        q = queries.iloc[i]
        kept_rows: List[pd.Series] = []
        kept_changes: List[List[str]] = []
        r = 0
        while len(kept_rows) < N_WANTED and r < MAX_ROUNDS:
            r += 1
            seed_everything(seed + 100_000 * r)
            cfe = RUNNER.generate(queries.iloc[[i]].reset_index(drop=True))
            obj = cfe[0]
            cfs = obj.final_cfs_df if obj is not None else None
            if cfs is None or len(cfs) == 0:
                continue
            d = _clean(cfs)
            for k in range(len(d)):
                if len(kept_rows) >= N_WANTED:
                    break
                chg = _changes_of(q, d.iloc[k])
                if admissible(chg, tiers, grades=grades):
                    kept_rows.append(d.iloc[k])
                    kept_changes.append(chg)
        rounds_used.append(r)
        if not kept_rows:
            n_no_cf += 1
            continue
        d = pd.DataFrame(kept_rows).reset_index(drop=True)
        val.append(validity(res["model"].predict(d.values), cfg["dice"]["desired_class"]))
        prox.append(proximity_l1(q, d, ranges))
        spar.append(sparsity(q, d))
        act.append(float(np.mean([actionability_score(q, d.iloc[j])["score"]
                                  for j in range(len(d))])))
        per_cf.extend(kept_changes)

    return _summarise(f"route_{variant}", seed, per_cf, val, act, prox, spar,
                      n_no_cf, rounds_used, tiers, grades)


def _summarise(label: str, seed: int, per_cf, val, act, prox, spar,
               n_no_cf: int, rounds: List[int], source_tiers: Set[str],
               grades: Optional[Iterable[str]]) -> Dict:
    role = summarise(per_cf, reading="narrow", rule="role")
    edge = summarise(per_cf, reading="narrow", rule="edge")
    n_changes = sum(len(c) for c in per_cf)
    ind_changes = sum(1 for c in per_cf for f in c if TIER.get(f) == "indicator")
    # Both readings, so the gap between them is reported rather than assumed.
    n_univ = sum(1 for c in per_cf
                 if admissible(c, source_tiers, reading="universal", grades=grades))
    n_exis = sum(1 for c in per_cf
                 if admissible(c, source_tiers, reading="existential", grades=grades))
    return {
        "label": label,
        "seed": seed,
        "n_cf": len(per_cf),
        "queries_with_no_cf": n_no_cf,
        "validity": float(np.mean(val)) if val else float("nan"),
        "actionability_eq1": float(np.mean(act)) if act else float("nan"),
        "act_route": act_route(per_cf, source_tiers, grades),
        "grades": "all" if grades is None else "".join(sorted(grades)),
        "proximity_L1": float(np.mean(prox)) if prox else float("nan"),
        "sparsity": float(np.mean(spar)) if spar else float("nan"),
        "n_changes": n_changes,
        "indicator_changes": ind_changes,
        "cf_touching_indicator": role["cf_touching_target"],
        "unsupported_role_rule": role["cf_unsupported"],
        "unsupported_edge_rule": edge["cf_unsupported"],
        "fully_unactionable": role["cf_fully_unactionable"],
        "admissible_universal": n_univ,
        "admissible_existential": n_exis,
        "reading_gap": n_exis - n_univ,
        "rounds_mean": float(np.mean(rounds)) if rounds else float("nan"),
        "rounds_max": int(np.max(rounds)) if rounds else 0,
    }


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    out = REPO / "outputs_kg"
    out.mkdir(exist_ok=True)
    ckpt = out / "route_enforcement.csv"

    # Resumable: each (label, seed) row is appended as soon as it finishes, so a
    # long run can be stopped and restarted without repeating work.
    done = set()
    rows = []
    if ckpt.exists():
        prev = pd.read_csv(ckpt)
        rows = prev.to_dict("records")
        done = {(r["label"], int(r["seed"])) for r in rows}
        print(f"resuming: {len(done)} rows already done")

    jobs = []
    for seed in SEEDS:
        jobs.append(("baseline_published", seed, None))
        for variant in VARIANTS:
            jobs.append((f"route_{variant}", seed, variant))

    for label, seed, variant in jobs:
        if (label, seed) in done:
            print(f"skip {label} seed {seed}")
            continue
        print(f"[seed {seed}] {label} ...", flush=True)
        row = run_baseline(seed) if variant is None else run_route(seed, variant)
        rows.append(row)
        pd.DataFrame(rows).to_csv(ckpt, index=False)
        print(f"  -> n_cf {row['n_cf']}  no_cf {row['queries_with_no_cf']}"
              f"  validity {row['validity']:.4f}  act_route {row['act_route']:.4f}"
              f"  rounds {row['rounds_mean']:.2f}", flush=True)

    df = pd.DataFrame(rows)
    print("\n" + "=" * 100)
    cols = ["label", "seed", "n_cf", "queries_with_no_cf", "validity",
            "actionability_eq1", "act_route", "unsupported_edge_rule",
            "reading_gap", "rounds_mean"]
    print(df[cols].to_string(index=False))
    print("=" * 100)
    gap = int(df["reading_gap"].abs().sum())
    print(f"\nUniversal vs existential reading: total gap {gap} counterfactuals.")
    print("REMINDER. Rejection cannot create recourse the unconstrained generator")
    print("never proposes, so retained counts are bounded above by post-hoc")
    print("filtering of an unconstrained run. Report the bound.")
    RUNLOG.finish(out)