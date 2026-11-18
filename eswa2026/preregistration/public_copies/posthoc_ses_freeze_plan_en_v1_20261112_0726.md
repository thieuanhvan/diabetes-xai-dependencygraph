# Post-hoc plan S-P1, S-P2, S-P3: socio-economic freeze, split stability and native Actionable Recourse cost

Written 12/11/2026 07:26 (machine time), before any run it describes. Requested in the revision round after the blind review of the ESWA v2 manuscript, approved on 12/11/2026. Frozen by its SHA-256 in `MANIFEST_sha256.txt` together with the code it names, and logged as S-P1, S-P2 and S-P3 in `deviations_log_q1_en.md`.

## 1 Status and labelling

- The frozen prereg (`prereg_q1_extension_en_v3_20261111_1645.md`, SHA-256 95a83da5…112369d) and its verdicts stay primary. Nothing here changes H1–H5 or supports a claim at a stated error rate.
- All three analyses are post hoc and exploratory. They were chosen after the A2 and extension B results, and after a reviewer pointed to the issues below. Every number they produce is labelled "post hoc (S-P1/S-P2/S-P3)" wherever it appears. The decision rules of H1–H3 are applied descriptively ("rule met", "rule not met", "undecided"), not as verdicts.
- Results already seen: all A2 CKD results (seed-42 split), all extension B results, the B-P1 post-hoc results, and the reviewer's recount of socio-economic changes in the A2 files (35.19% of CKD DiCE published counterfactuals touch Income, Education or AnyHealthcare; 9.28% change only these). No run described below has been started.

## 2 S-P1: socio-economic features frozen in CKD

Issue. The CKD role table gives Education, Income and AnyHealthcare the graph role "immutable" (no route to the outcome), but the generator constraint is the direction inherited from the earlier taxonomy ("monotonic up"), so generators could increase them. The audit's "fully unactionable" counts such changes as non-actions only when an indicator is also touched.

Run. The frozen A2 scripts, called through a thin wrapper (`tools/q1_posthoc_ses_splits/ps_ckd_runs.py --tag ses_freeze --ses-freeze`) that, in memory, also makes Education, Income and AnyHealthcare immutable in every mode. Everything else as A2: pooled NHANES CKD analytic table (hash-checked), split 80/20 stratified seed 42, XGBoost of configs/default.yaml, main cohort (p ≥ 0.5, at most 200), DiCE random with generator seeds 42, 123, 2024, 7, 31337 in published, lock and route-aware modes (KDIGO graph, k = 1, regeneration up to 8 rounds), and the exhaustive search in published, lock, route-aware and capped modes. Check before any counterfactual: the seed-42 refit equals the frozen A2 test probabilities (else stop). The frozen A2 analysis script then computes O-A1, the movability null (movable sets now exclude the three features), O-A3 and lock coverage, O-A5 and O-A4, and the software checks, with the same bootstrap seeds and rules.

Descriptive companion (no new run). From the existing per-counterfactual files, the shares of counterfactuals that touch any of the three features and that change only these features, and the share with no lever and no treatable change: CKD DiCE random (published, lock, route-aware) and exhaustive search (each mode, all returned and best), and the diabetes DiCE random and exhaustive files behind main Table 3 and Supplementary Table S17, and the extension B generators (Actionable Recourse, Growing Spheres, Wachter on LR). CholCheck (diabetes only, also "monotonic up") is reported on one line. Script `ps_ses_shares.py`, written after this plan and hashed when written; it only reads files.

## 3 S-P2: stability over train/test splits (CKD headline)

Run. The same wrapper without the socio-economic freeze (`--split-seed s`), with s = 11, 22, 33, 44, 55: the split seed and the XGBoost random_state are both s; every hyperparameter is unchanged. Per split: refit, cohort by the A2 rule (floor 50; below it the split is "not reached" and reported), DiCE random in three modes with the same five generator seeds, exhaustive search, and the frozen A2 analysis.

Reported per split and as a range over splits (with the seed-42 result beside them): test AUC, cohort size, O-A1 (fully unactionable share) with its one-sided 99% lower bound and the movability p, O-A3 (H2 Δ valid among requested) with its lower bound and lock coverage, O-A5 (H3 difference) with its 98% interval, the share of patients with difference exactly 0, and O-A4. The H1–H3 rules are applied descriptively.

Run time. Two processes at a time (S-P1 with split 11 first, then splits 22 and 33, then 44 and 55). If after the first pair the projected wall time for all five splits exceeds three hours from the start of the first pair, only splits 11, 22 and 33 are run, and this is stated. No split is dropped for its results.

## 4 S-P3: Actionable Recourse with its native cost

Run. `ps_ar_native.py`: the frozen extension B Actionable Recourse setting on the BRFSS 2021 logistic regression (same fitted pipeline, cohort, action grid, flipset of 5, lock and route constraints), with the objective replaced by the maximum percentile shift of Ustun et al. (2019): the percentile of a value is the empirical CDF of the feature on the training split, the cost of an action is the absolute change in percentile, the objective is the largest such change over the features acted on, with 0.001 times the sum as a tie-break. Analysed with the frozen `b_analysis.describe` and `movability_null`; the frozen L1-cost outputs are re-analysed by the same code and must reproduce the reported fully unactionable share 0.7300 (else stop). Reported: coverage, touch, unsupported (ADA, k = 1), fully unactionable, movability p, socio-economic shares, Δ valid (lock − published), for both costs side by side.

## 5 Environment and outputs

- Python with `-I`, below-normal priority, at most two heavy processes on the machine, OMP_NUM_THREADS not set by us (the frozen A2 scripts are unchanged). CKD runs in the P4 venv (as A2, C12); AR in the p7-carla312 venv (as extension B).
- Outputs: `outputs/q1_posthoc_ses_splits/` (one folder per run tag, `ar_lr_mps/`, and the summary JSON and note). Numbers truncated to 4 decimals, never rounded.
