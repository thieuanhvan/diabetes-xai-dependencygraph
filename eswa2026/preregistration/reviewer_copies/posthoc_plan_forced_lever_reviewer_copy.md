*Reviewer copy for anonymised review. Original SHA-256 b1c7624aea42fa4e7911e869db77e71f44ccbe9dc983416acaf53c214cdf87e0; 13 substitutions (author and personal references, internal project codes, local paths, review records, non-English approval quotes). The unredacted original will be deposited with the artefact DOI.*

# Post-hoc plan S-P4: lock plus forced lever, a graph-free baseline for route-aware enforcement

Written 12/11/2026 09:57 (machine time), before any run it describes. Requested in the revision round after an internal pre-submission review, approved by the authors on 12/11/2026. Frozen by its SHA-256 in `the authors' hash manifest` together with the code it names, and logged as S-P4 in `deviation_log_reviewer_copy.md` before the first run.

## 1 Status and labelling

- The frozen prereg (`preregistration_reviewer_copy.md`, SHA-256 95a83da5…112369d) and its verdicts stay primary. H4 and H5 stay NOT REACHED (B-E2). Nothing here changes a preregistered verdict or supports a claim at a stated error rate.
- Everything here is post hoc and exploratory. It is chosen after the B-P1 results (Wachter on refitted MLPs), the extension B results (Wachter/LR) and the A2 and S-P1 CKD results were seen, and after a reviewer pointed out that the route-aware coverage on MLP seeds 46, 48 and 49 may come from the search procedure rather than from the graph. Every number it produces is labelled "post hoc (S-P4)".
- Results already seen: all A2, S-P1 to S-P3 and extension B results, all B-P1 results (published, lock and route-aware rows and kept outputs of MLP seeds 44, 45, 46, 48 and 49), and the reviewer's figures: on seed 46 route-aware covers 139 of 200 patients and published 29; 0.757 of route-aware runs and 0.105 of published runs are valid before rounding; 9.73% of lock runs are valid before rounding and none after. No forced-lever run has been started.

## 2 Question

Route-aware enforcement (prereg 5.3) differs from the indicator lock in two ways at once: (a) in 23 of its 24 patterns it forces one to three levers to move at least one grid step, which changes the start of the search, the box and the path of the optimiser; (b) it frees an indicator when a graph edge links it to a forced lever. The question is whether the coverage gain of route-aware over lock on the MLP seeds comes from (b), which needs the graph, or from (a), which does not.

## 3 Modes

All modes use the frozen generator code and settings of extension B and B-P1 (`b_methods.wachter_rows` and `finish_rows`, `b_wachter_core`, the B-D1 cap, P = 24 runs per generator seed, generator seeds 42, 123, 2024, 7, 31337, the same random starts s(x) + N(0, 0.01²) from `default_rng(seed · 1000 + j)`, the same rounding psi, the same kept-output rule: valid rounded result of lowest scaled L1 cost per seed, ties to the lowest j) and the same 4 CPU-hour budget per seed × mode. Only the grids of each run differ.

- **published, lock, route-aware**: the existing B-P1 and extension B runs, not rerun.
- **forced-lever, generic (FL-G, primary)**: the indicator lock (GenHlth, PhysHlth and MentHlth immutable, the BRFSS lock of prereg 2; on CKD the lock set is {GenHlth, MentHlth}, Section 5) plus one forced feature per run, chosen with no graph edge and no route information. The candidate set F is every feature whose role is lever or treatable, in role-table order: BMI, PhysActivity, Fruits, Veggies, Smoker, HvyAlcoholConsump, NoDocbcCost, HighBP, HighChol (9 features). Run j = 1 forces nothing (it equals the lock run j = 1, as route-aware pattern 1 does); run j = 2, …, 24 forces F[(j − 2) mod 9], so each feature is forced in two or three runs with different random starts. Budget: 24 runs per seed, as route-aware.
- **forced-lever, route-matched (FL-R, secondary)**: the indicator lock plus, in run j, exactly the levers that route-aware pattern j forces (pattern 1: none). It uses the graph only to choose which levers to force and never frees an indicator, so FL-R versus route-aware isolates the effect of freeing indicators along graph edges.
- **Forcing rule** (as B-C1 d, applied to any feature): a forced feature u has G_u restricted to values at least one grid step from x_u in its permitted direction of the taxonomy study; for a bidirectional feature (BMI only) the side whose nearest forced value gives the higher class-0 probability (tie: down). A run whose forced feature cannot move for the patient (no such value) is infeasible, yields no output and still counts as one of the 24 runs. Indicators keep the lock grid {x_v}. Every other feature keeps its published grid, so the socio-economic features are movable exactly as in the published, lock and route-aware runs they are compared with.

## 4 Models and cohorts (BRFSS 2021 diabetes)

- Wachter on the post-hoc MLPs of B-P1, seeds 46, 48 and 49 (the seeds behind the manuscript's claim) and the other accepted seeds 44 and 45; each seed's own cohort (`outputs/q1_ext_b_posthoc/models/mlp_s<seed>/cohort.csv`, 200 patients).
- Wachter on the frozen extension B logistic regression (`outputs/q1_ext_b/models/lr`), its cohort of 200, if the run time allows (expected minutes).
- Before the runs of each model, the batched core is checked against the single-run core on cohort patient 0 (frozen `b_run_wachter.precheck`, ≤ 1e-4); run j = 1 of FL-G is compared with lock run j = 1 (same grids, same start) and the share of identical (valid_post, change set) pairs is reported (expected 1; a lower value is reported, not a stop, because batch composition can change floating-point order).

## 5 CKD (NHANES, XGBoost, main cohort)

The CKD route-aware mode has no lever-forcing patterns: DiCE random is generated in published mode and filtered by the KDIGO path rule with up to 8 regeneration rounds (seed + 100,000 r), and the exhaustive search filters change sets. The graph-free analogue is therefore:

- **DiCE random, lock plus forced lever**: generation in lock mode ({GenHlth, MentHlth} immutable), a returned counterfactual is accepted only when its change set contains at least one lever or treatable (BMI, Smoker, PhysActivity, HighBP, HighChol), with the same regeneration rule and budget as route-aware (up to 8 rounds, 5 requested per seed, generator seeds 42, 123, 2024, 7, 31337).
- **Exhaustive search, lock plus forced lever**: the frozen value-returning copy `search_full` under the lock with the set filter "contains a lever or treatable".
- Two configurations: socio-economic features frozen (S-P1 configuration, the primary configuration of an earlier draft) and the frozen prereg configuration (socio-economic features movable, A2). The model is refitted with the frozen settings and must equal the frozen A2 test probabilities (else stop); the cohort rebuilt by the A2 rule must equal the saved cohort of that configuration (else stop).

## 6 Outcomes

Per model (or seed) and mode:

- Patient coverage: patients with at least one kept output (Wachter) or at least one valid counterfactual (CKD), count and share with Clopper–Pearson 95% interval.
- Valid among requested: kept outputs / 5 per patient (Wachter); valid counterfactuals / 25 (CKD DiCE).
- Wachter only, over feasible runs: share valid before rounding, share valid after rounding, share valid before and not after rounding (lost at rounding); number of patients with at least one run valid before rounding; mean iterations; share of runs that reach the outer lambda cap (last lambda step).
- Over kept outputs (Wachter) or all returned counterfactuals (CKD, the O-A1 denominator of C11): share touching an indicator, share changing GenHlth, share with no lever and no treatable change (counts socio-economic-only outputs), share changing only socio-economic features, mean scaled L1 cost.
- CKD exhaustive: coverage and mean best cost; best-cost difference forced-lever minus route-aware on patients with a best counterfactual in both.

## 7 Pre-declared reading

Primary quantity: Δ_G = coverage(route-aware) − coverage(FL-G), pooled over MLP seeds 46, 48 and 49 (unit = seed × patient, 600 units), with a 95% cluster bootstrap interval that resamples test patients (identified by test position) with all their units, 2,000 resamples, `default_rng(20261111)`. Margin m = 0.10 (20 of 200 patients per seed).

- If the upper 95% bound of Δ_G is at most m, the coverage advantage of route-aware over lock is attributed to lever forcing, not to the graph. The manuscript then limits the graph's claim to provenance, auditability (queryable verdicts with sources) and the choice of which levers to force, and removes every statement that the graph keeps recourse where the lock loses it.
- If the lower 95% bound of Δ_G is above m, the graph adds coverage beyond generic lever forcing on these networks, and the manuscript may say so, labelled post hoc (S-P4), with the FL-G number beside it.
- Otherwise the result is undecided; the manuscript reports the point estimate and interval and makes no coverage claim for the graph.

Secondary, read the same way: Δ_R = coverage(route-aware) − coverage(FL-R) on the same units (effect of freeing indicators along edges, given the same forced levers); the same Δ_G and Δ_R per seed (descriptive, Clopper–Pearson for each coverage), pooled over all five accepted seeds (descriptive), on Wachter/LR (descriptive), and on CKD DiCE (Δ = coverage(route-aware) − coverage(forced-lever) over 188 patients, patient bootstrap, same margin, descriptive).

## 8 Checks of the manuscript text (read only)

From the existing B-P1 rows: the reviewer's figures above, the iteration and cap shares, and the sentence "every valid output of these networks needed a GenHlth change" (an earlier draft), which is tested by counting lock runs valid before rounding and published kept outputs without a GenHlth change. A sentence the data contradict is corrected or removed.

## 9 Presentation-layer companion (read only, no new run)

For the route-aware outputs that exist (Actionable Recourse/LR with both costs, Wachter on LR and on the MLP seeds, CKD DiCE and exhaustive), each output is split into actions (lever and treatable changes), socio-economic changes and expected consequences (indicator changes, shown as consequences, never as actions). Reported: share of outputs with an indicator change, share with at least one action, share whose action list is empty or socio-economic only, and the share in which GenHlth changes.

## 10 Environment, code and outputs

- the CARLA environment venv for Wachter, the taxonomy study venv for CKD (as C12), `python -I`, below-normal priority, one heavy process at a time (a separate hypertension job uses the other slot), OMP_NUM_THREADS not set by us.
- Code: `<local path>` (`fl_run_wachter.py`, `fl_ckd_runs.py`, `fl_analysis.py`), importing the frozen modules unchanged; hashed into the manifest before the first run. A fix after the first run is logged as an engineering entry with a new hash.
- Outputs: `outputs/q1_posthoc_forced_lever/` (one folder per model, CKD folders per configuration, `analysis/forced_lever_results.json` and a note). Numbers truncated to 4 decimals, never rounded.
