# Architecture

Internal documentation for `diabetes-xai-dependencygraph`. Audience: future maintainer.

## Overview

This repository adds one axis to the published knowledge layer and audits the
published counterfactuals against it.

```
published pipeline (diabetes-xai-counterfactual @ v1.0-ijmi, imported read-only)
    ->  run_audit_dump.py    reproduce per-query CFs, dump raw per-CF changes
                             -> outputs/raw_cf_changes.csv, raw_cf_index.csv
    src/depgraph/                   the dependency graph K_G
        nodes.py             role tier per feature (lever/treatable/indicator/immutable)
        edges.py             u -> v edges, each an ADA recommendation + grade
        audit.py             THE audit rule, one place, both variants
    ->  analysis/audit_rules.py    re-audit dumped CFs offline, no model needed
    ->  analysis/export_edges.py   full 26-edge table for the appendix
    ->  analysis/test_audit.py     hand-checked regression test
    ->  run_enforce.py       exclude indicators from features_to_vary; re-run
                             -> outputs/graph_cf_*.csv, enforcement_comparison.csv
    ->  run_seed_sweep.py    both configs over seeds {42,123,2024,7,31337}
                             -> outputs/seed_sweep.csv
    ->  analysis/make_figures.py   Figure 1 from src/depgraph/
```

## The one design rule

The published pipeline is a frozen, published artifact. Nothing here writes into
it. `run_*.py` add `PIPELINE_REPO` to `sys.path` and import `src.pipelines.*`;
the taxonomy is patched in memory (`FT.FEATURE_TAXONOMY[f] = ...`), never on disk.
This repo's own module lives under `src/depgraph/` and is imported as `depgraph.*` (its `src/`
is added to the path separately), so the two `src/` directories never collide.

## Module responsibilities

`src/depgraph/nodes.py`: `TIER` maps each of the 21 BRFSS features to a role tier;
`DIRECTION` reproduces the published direction class verbatim so that any measured
difference is attributable to the tier axis alone. `STRICT_INDICATORS` supports
the both-readings analysis (HighBP/HighChol as treatable vs indicator).

`src/depgraph/edges.py`: `EDGES` is the edge list; each `Edge` carries its ADA source
and grade. `in_neighbours(v)` returns the levers with an edge into `v`, which is
the audit rule's core query. `NO_GUIDELINE_TARGETS_INDICATORS` records the
decisive negative result (no ADA recommendation targets an indicator).

`src/depgraph/audit.py`: the audit rule of Section IV-E, isolated so it has exactly one
definition. Two variants are implemented on purpose:

    rule="edge"   a change to an indicator v is UNSUPPORTED unless the
                  counterfactual also changes some lever u with (u -> v) in E.
                  This is what the paper defines.
    rule="role"   a change to an indicator is UNSUPPORTED unless the
                  counterfactual changes ANY lever. This ignores E, and is what
                  run_seed_sweep.py inlined before this module existed.

They disagree: on seed 42, `role` flags 171 counterfactuals and `edge` flags 205.
The 34-counterfactual difference is the work the edge set does that a role label
cannot do, and it must be reported rather than assumed. `analysis/audit_rules.py`
recomputes both from the dumped CSVs in under a second and writes the difference
to `outputs/audit_rule_diff.csv`.

A caution that belongs in the paper: no GRADED edge reaches the indicator tier.
`lever_in_neighbours("GenHlth", grades="ABC")` is empty. All indicator support
comes from the eight narrative edges, so restricting the graph to graded edges
makes all 332 indicator-touching counterfactuals unsupported. The twelve grade-A
edges only matter under the broad reading, where treatables are also targets.

## Re-auditing after a change to the graph

Changing `nodes.py` or `edges.py` does not require regenerating counterfactuals:

    python analysis/test_audit.py        # sanity, no data needed
    python analysis/audit_rules.py       # re-audit the dumped CFs
    python analysis/export_edges.py      # refresh the appendix table
    python analysis/make_figures.py      # refresh Figure 1

`run_seed_sweep.py` now dumps `sweep_changes_seed<S>_<config>.csv` for every seed
and configuration, so the same offline re-audit works for the multi-seed results
once the sweep has been run once.

## A note on the dumps under `outputs/`

The counterfactual dumps (`raw_cf_*.csv`, `graph_cf_*.csv`, `seed_sweep.csv`,
`enforcement_comparison.csv`, `audit_rule_*.csv`, `tier_sensitivity.csv`) are
derived files. They are **not** shipped inside release archives, because
extracting an archive over a checkout would overwrite a fresh run with an old
snapshot and give it a new timestamp, which is indistinguishable from a fresh
run if you sort by modification time.

`depgraph.paths.find_dump` therefore resolves by search order, not by timestamp: the
directory the runners write to wins. Override with `KG_OUTPUTS=/some/dir`.

`python analysis/check_install.py` prints the row count of the dump it would
read, which is the quickest way to confirm which run is about to be analysed.
