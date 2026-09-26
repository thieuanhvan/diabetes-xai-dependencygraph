# outputs/

Committed result files for the FAIR 2026 paper. Each file below is the source
of the numbers cited in the paper, with one exception noted.

| File | Run | Used in the paper |
|---|---|---|
| `raw_cf_changes.csv`, `raw_cf_index.csv` | seed 42, discarded global-mode pass **replayed** (1,520 changes; reproduces the published vector at L1 = 0) | Section V, Table IV |
| `audit_rule_comparison.csv`, `audit_rule_diff.csv` | derived from the replayed seed-42 dump | Section V-C (role rule 172, edge rule 210, fully unactionable 111) |
| `tier_sensitivity.csv` | derived from the replayed seed-42 dump | Section VII (210 -> 323; 268) |
| `seed_sweep.csv` | five seeds {42, 123, 2024, 7, 31337}, replayed | Section V-E, Table V (five-seed ranges and means) |
| `route_enforcement.csv` | five seeds, route-aware enforcement | not in the conference paper (reserved for the journal extension) |
| `model_reproducibility.csv` | classifier reproduction check | Section V-A (AUC 0.8233) |
| `edges_full.csv`, `edges_full.tsv` | the 26 edges of K_G | Section IV-D (complete edge set) |
| `enforcement_comparison.csv` | **seed 42, constrained pass only, NOT replayed** (1,500 changes) | **not used**: kept for provenance of the 1,500-vs-1,520 gap explained in Section V-A. The paper's enforcement numbers come from `seed_sweep.csv`. |

The runners write to `PIPELINE_REPO/outputs_kg`; `refresh_outputs.bat` copies a
finished run here. See ARCHITECTURE.md.
