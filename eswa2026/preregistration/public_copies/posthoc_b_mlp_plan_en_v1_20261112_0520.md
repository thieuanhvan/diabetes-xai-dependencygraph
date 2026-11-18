# Post-hoc plan B-P1: Wachter on refitted MLPs (P7 Q1 extension B)

Written 12/11/2026 05:20 (machine time), before any post-hoc model is fitted. Approved by the student on 12/11/2026 ("Có, hậu kiểm"). Frozen by its SHA-256 in `MANIFEST_sha256.txt` and logged as B-P1 in `deviations_log_q1_en.md`.

## 1 Status and labelling

- The frozen prereg (`prereg_q1_extension_en_v3_20261111_1645.md`, SHA-256 95a83da5…112369d) stays primary. Under its 5.4 rule 4, H4 and H5 are NOT REACHED (event B-E2: the preregistered MLP with seed 42 is a constant function; 0 of 3 units of the last hidden layer are live, every test patient gets p = 0.1421, the cohort is empty).
- Everything in this plan is post hoc and exploratory. The seed is changed after a result (the degenerate seed-42 network) was seen. Nothing here counts toward H4 or H5, changes their verdict, or supports an alpha claim. Every number from this plan is labelled "post hoc (B-P1)" wherever it appears.
- No counterfactual of the Wachter/MLP pair has been seen by anyone. The secondary pairs (Wachter/LR, Growing Spheres/XGBoost, Actionable Recourse/LR, MINT/XGBoost) have been run and their results seen; they are not changed by this plan.

## 2 Models: architecture and training exactly as preregistered, only the seed varies

- Code: the frozen `b_models.train_mlp` (vendored CARLA ANN, hidden 18, 9, 3, ReLU, softmax output; Adam lr 0.002; batch 1,024; 20 epochs; BCE on the softmax output against one-hot labels, B-D2; P4-range scaled inputs; same data, split and features). The only change is the seed s, used where seed 42 was used: `torch.manual_seed(s)` before the net is built and the DataLoader shuffle generator seeded s. Torch threads 2, as the frozen script.
- Seeds are tried in the order 43, 44, 45, …, one at a time.
- **Live unit:** a hidden unit is live when its ReLU output is > 0 for at least one training row. Counted per hidden layer on the trained network (the acceptance criterion) and, for information, at initialisation.
- **Eligible patients:** test patients with p ≥ 0.5, where p = softmax probability of class 1.
- **Acceptance:** a seed is accepted only if (a) every hidden layer of the trained network has at least one live unit on the training data, and (b) at least 50 test patients are eligible.
- **Stopping:** stop after 5 accepted seeds or 30 seeds tried, whichever comes first. No seed is skipped, re-ordered, or excluded for any other reason.
- **Reported for every seed tried:** live units per hidden layer (trained and at initialisation), test AUC, number of eligible patients, accepted or not, and the reason for rejection.

## 3 Primary post-hoc pair: Wachter on each accepted MLP

Run exactly as the prereg's Wachter protocol and the frozen extension B code (`b_methods`, `b_wachter_core`, unchanged, with deviations B-D1 and clarifications B-C1 as logged):

- CARLA core with the `t_max_min` wall-clock rule disabled; vendored defaults lr 0.01, lambda 0.01, 1,000 iterations per lambda step, `lamb -= 0.05`, outer cap of 10 lambda steps (B-D1), L1 norm, BCE, target class 0.
- Cohort: the P7 rule on that seed's model (test patients with p ≥ 0.5, at most the 200 highest-risk).
- Generator seeds per patient: 42, 123, 2024, 7, 31337 (5 seeds). In every mode P = 24 runs per seed: published and lock from random starts s(x) + N(0, 0.01²) with sub-seeds seed·1,000 + j, route-aware one run per ADA pattern with the same sub-seeds. Kept output per seed = valid rounded result of lowest scaled L1 cost (route-aware: also passing the path constraint).
- Modes: published, lock (GenHlth, PhysHlth, MentHlth immutable), route-aware.
- Validity: argmax of the softmax is class 0 at the rounded point (B-C1 c); validity before rounding also recorded.
- Before the runs of each seed, the batched core is checked against the single-run core on cohort patient 0 (4 rows, ≤ 1e-4 per coordinate); a mismatch stops that seed.
- Budget: 4 CPU-hours of process CPU time per seed × mode. Exceeding it makes that seed × mode "not reached (CPU budget)".

## 4 Outcomes and statistics

Same metrics and code as H4/H5 in `b_analysis.py` (C9, C11, B-C1 i), computed per accepted seed:

- **Fully unactionable share** (published), per patient over the kept outputs; patients without kept output excluded and counted.
- **Movability null** (published): the frozen per-patient enumeration, 100,000 Monte Carlo draws, seed 20261111.
- **Valid among requested**, lock minus published (kept outputs / 5 per patient).
- **Lock patient coverage** (at least one kept output), point estimate with Clopper–Pearson 95% and 99% intervals.
- Secondary, as `b_analysis`: route-aware vs lock best kept cost (TOST, δ = 0.05, 98% interval), leakage under the four readings, touch share, O-share, costs, change counts, validity before and after rounding, distinct outputs, change sizes, CPU time.

Intervals: percentile bootstrap, 2,000 resamples, fresh `default_rng(20261111)` per metric; two-sided 95% and 99% intervals, and the one-sided 99% bounds (1st / 99th percentiles) used by the decision rules. Proportions of patients: Clopper–Pearson 95% and 99%.

**Decision rules, descriptively.** For each accepted seed, the H4 and H5 rules of prereg 5.5 are applied to the post-hoc numbers and reported as "rule met", "rule not met" or "rule undecided" (same thresholds: H4 lower one-sided 99% bound of the fully unactionable share > 0.10 and movability p < 0.01; H5 lower one-sided 99% bound of the change in valid among requested > −0.05 and lock coverage ≥ 0.95). These are descriptions, not verdicts: no hypothesis is supported or rejected by them.

**DiCE-like failure.** The DiCE-like indicator failure of P7 is said to appear for Wachter/MLP at a seed when the H4 rule is met at that seed. The fully unactionable share, its intervals and the movability p are reported for every seed whatever the outcome.

**Pooled summary** over the accepted seeds:

- Unit = (seed, test patient) in the cohort of that seed. Cohorts overlap across seeds, so units are not independent; intervals use a cluster bootstrap that resamples test patients (identified by their test index) with all their units, 2,000 resamples, `default_rng(20261111)`, 95% and 99% two-sided intervals and one-sided 99% bounds.
- Pooled fully unactionable share (units with a kept output), pooled change in valid among requested, pooled lock coverage (share of units with a lock output; cluster bootstrap interval).
- Pooled movability null: the frozen per-patient null with each unit as a patient (100,000 draws); descriptive only, since units are clustered.
- Number of accepted seeds meeting each rule; median, minimum and maximum of the per-seed estimates.

## 5 What is reported, including failure

- The full seed table (every seed tried) and the stopping reason.
- 5 accepted seeds: per-seed results and the pooled summary.
- 1 to 4 accepted seeds after 30 tried: the same, for the accepted seeds only, with the shortfall stated; nothing else is tried.
- 0 accepted seeds: the seed table only; Wachter/MLP is "not reached" post hoc as well, and no other model, architecture or method replaces it.
- A seed × mode stopped by the CPU budget is reported as not reached; the rules needing it are "not reached" for that seed.
- All tried and accepted seeds are reported; none is dropped because of its counterfactual results.

## 6 Additional item (not part of B-P1's question)

The 99% bootstrap bounds of the secondary Actionable Recourse/LR fully unactionable share (published, point 0.73) are computed from the frozen `outputs/q1_ext_b/ar_lr/out_published.csv` with the frozen `b_analysis.describe` and the same bootstrap (2,000, `default_rng(20261111)`): two-sided 99% interval and one-sided 99% bounds. The script must reproduce the reported point estimate 0.73 and 95% interval [0.6789, 0.775] first, otherwise it stops. Reported as a clearly marked addition.

## 7 Environment and outputs

- p7-carla312 venv, `python -I`, below-normal priority, at most two heavy processes on the machine, OMP_NUM_THREADS not set (B-E3), BLAS limited to 2 threads by `b_common`.
- Code: `<local>`, importing the frozen extension B modules unchanged; scripts hashed into the manifest before the first fit.
- Outputs: `outputs/q1_ext_b_posthoc/` (models per seed, Wachter runs per seed, analysis JSON, results note).
- Numbers are truncated to 4 decimals in notes, never rounded.
