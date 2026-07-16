# Architecture

Internal documentation for `diabetes-xai-kg`. Audience: future maintainer.

## Overview

This repository adds one axis to the published knowledge layer and audits the
published counterfactuals against it.

```
published pipeline (diabetes-xai-counterfactual @ v1.0-ijmi, imported read-only)
    ->  run_audit_dump.py    reproduce per-query CFs, dump raw per-CF changes
                             -> outputs/raw_cf_changes.csv, raw_cf_index.csv
    src/kg/                   the dependency graph K_G
        nodes.py             role tier per feature (lever/treatable/indicator/immutable)
        edges.py             u -> v edges, each an ADA recommendation + grade
    ->  audit rule           a change to an indicator v is UNSUPPORTED if the CF
                             changes no lever u with (u -> v) in E
    ->  run_enforce.py       exclude indicators from features_to_vary; re-run
                             -> outputs/graph_cf_*.csv, enforcement_comparison.csv
    ->  run_seed_sweep.py    both configs over seeds {42,123,2024,7,31337}
                             -> outputs/seed_sweep.csv
    ->  analysis/make_figures.py   Figure 1 from src/kg/
```

## The one design rule

The published pipeline is a frozen, published artifact. Nothing here writes into
it. `run_*.py` add `PIPELINE_REPO` to `sys.path` and import `src.pipelines.*`;
the taxonomy is patched in memory (`FT.FEATURE_TAXONOMY[f] = ...`), never on disk.
This repo's own module lives under `src/kg/` and is imported as `kg.*` (its `src/`
is added to the path separately), so the two `src/` directories never collide.

## Module responsibilities

`src/kg/nodes.py`: `TIER` maps each of the 21 BRFSS features to a role tier;
`DIRECTION` reproduces the published direction class verbatim so that any measured
difference is attributable to the tier axis alone. `STRICT_INDICATORS` supports
the both-readings analysis (HighBP/HighChol as treatable vs indicator).

`src/kg/edges.py`: `EDGES` is the edge list; each `Edge` carries its ADA source
and grade. `in_neighbours(v)` returns the levers with an edge into `v`, which is
the audit rule's core query. `NO_GUIDELINE_TARGETS_INDICATORS` records the
decisive negative result (no ADA recommendation targets an indicator).
