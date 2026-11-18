*Reviewer copy for anonymised review. Original SHA-256 57ec4877ba3c278d28379cd20a38535c206e600a2b7c1e875835a09022edb8d8; 24 substitutions (author and personal references, internal project codes, local paths, review records, non-English approval quotes). The unredacted original will be deposited with the artefact DOI.*

# Post-hoc plan S-P5: diagnosis flags are not actions, a levers-only forced-lever baseline, and a matched three-disease comparison

Written 12/11/2026 12:11 (machine time), before any run or recomputation it describes. Requested in the revision round that follows an internal pre-submission review (issues M2 and M3), approved by the authors on 12/11/2026. Frozen by its SHA-256 in `the authors' hash manifest` together with the code it names, and logged as S-P5 in `deviation_log_reviewer_copy.md` before the first run.

## 1 Status and labelling

- The frozen prereg (`preregistration_reviewer_copy.md`, SHA-256 95a83da5…112369d), the HTN addendum v3 and plans B-P1 and S-P1 to S-P4 stay as they are; no preregistered verdict changes. H4 and H5 stay NOT REACHED (B-E2).
- Everything here is post hoc and exploratory, chosen after all A2, A2-HTN, extension B, B-P1 and S-P1 to S-P4 results were seen. Every number it produces is labelled "post hoc (S-P5)".
- Results already seen: all of the above, including the S-P4 reading (Delta_G 0.0950 [0.0326, 0.1549], undecided) and the reviewer's count that at MLP seed 46, 391 of the 471 FL-G outputs had HighBP or HighChol forced. No S-P5 run has been started and no S-P5 recount has been made.

## 2 Role reading R5 for the diabetes surveys

On BRFSS 2021, NHIS 2022 and 2024 and the harmonised NHANES diabetes tables, HighBP and HighChol record whether the respondent was ever told by a health professional that they have high blood pressure or high cholesterol (BRFSS, NHIS: self-report; NHANES harmonised table: BPQ020, BPQ080). Lowering them changes a diagnosis history, not a risk factor. NoDocbcCost records that the respondent could not see a doctor because of cost; it is an access barrier, not a health behaviour.

Reading R5 (primary from v5 on, for these surveys only):
- action features L5 = the genuine behaviours of the role table: BMI, PhysActivity, Fruits, Veggies, Smoker (down), HvyAlcoholConsump (NHIS and NHANES have only BMI, Smoker and PhysActivity);
- HighBP and HighChol: diagnosis history, non-actionable (immutable concept class of the role-derivation rule);
- NoDocbcCost: access barrier, non-actionable;
- indicators unchanged (GenHlth, PhysHlth, MentHlth, DiffWalk); all other roles unchanged.
- Sensitivity reading R5-7: as R5, with NoDocbcCost counted as an action (the seven role-table levers).

Metrics under R5 (and R5-7), over the same outputs and denominators as before:
- no action (R5): the change set is non-empty and contains no feature of L5;
- fully unactionable (R5): the change set touches an indicator and contains no feature of L5;
- unsupported: unchanged by construction in the primary reading (k = 1, lever sources); recomputed only to confirm.

Not affected: CKD and hypertension. There HighBP and HighChol are measured states (systolic pressure at least 130 mmHg; total cholesterol at least 240 mg/dL) and keep the role treatable.

## 3 Recomputation from existing outputs (no new run)

Read only, from the stored per-counterfactual files: DiCE random with XGBoost, logistic regression and random forest on the seven diabetes configurations (`outputs/crossdataset_t/results/`, the files used for Tables 4 and S13), DiCE genetic and the exhaustive search with the three classifiers (Tables S14, S16, S17), Actionable Recourse with both costs, Growing Spheres, MINT-style and projected Wachter on logistic regression (`outputs/q1_ext_b/`, `outputs/q1_posthoc_ses_splits/ar_lr_mps/`), projected Wachter on the five post-hoc networks (`outputs/q1_ext_b_posthoc/`, published, lock and route-aware kept outputs) and the presentation-layer counts. Each is reported under the v4 reading (lever or treatable is an action) and under R5 and R5-7, with the same patient means and bootstrap seeds as the original tables. The movability null does not depend on the action set and is not recomputed.

## 4 Levers-only forced-lever baseline (Wachter, rerun)

Mode FL-L ("levers"): identical to FL-G of plan S-P4 Section 3 (frozen loop, P = 24 runs per generator seed, generator seeds 42, 123, 2024, 7, 31337, the same starts, rounding, kept-output rule, B-C1 d forcing rule, 4 CPU-hour budget, indicator lock {GenHlth, PhysHlth, MentHlth}), except the candidate set: F_L = L5 in role-table order, BMI, PhysActivity, Fruits, Veggies, Smoker, HvyAlcoholConsump (6 features). Run j = 1 forces nothing; run j = 2, …, 24 forces F_L[(j − 2) mod 6], so each feature is forced in three or four runs. Every other feature keeps its published grid (HighBP, HighChol and NoDocbcCost stay movable exactly as in the published, lock, route-aware and FL-G runs they are compared with). Run 1 of FL-L is compared with lock run 1, as in S-P4.

Models and cohorts: the post-hoc MLPs of B-P1, seeds 46, 48 and 49 (primary) and 44 and 45, and the frozen extension B logistic regression, each with its own cohort of 200; batched-versus-single precheck as in S-P4.

FL-R (route-matched) forces only the route levers BMI, PhysActivity and Smoker, which all belong to L5, so it is already levers-only; it is not rerun and its S-P4 result is restated.

CKD forced-lever runs (S-P4 Section 5) are not rerun: in CKD the treatable features are measured states.

Outcomes as S-P4 Section 6, plus, per mode, the share of kept outputs that change HighBP or HighChol and the action coverage: patients with at least one kept output whose change set contains a feature of L5.

## 5 Pre-declared reading of the rerun

Primary: Delta_L = coverage(route-aware) − coverage(FL-L), pooled over MLP seeds 46, 48 and 49 (600 seed × patient units), 95% cluster bootstrap over test patients (2,000 resamples, `default_rng(20261111)`), margin m = 0.10, read as S-P4 Section 7:
- upper 95% bound ≤ m: the coverage advantage of route-aware enforcement over the lock is attributed to forcing a genuine lever; the S-P4 statement stands with levers only;
- lower 95% bound > m: route-aware enforcement adds coverage beyond forcing a genuine lever on these networks; the manuscript withdraws "forcing any lever recovered most of the coverage" and says so, labelled post hoc (S-P5);
- otherwise undecided; the manuscript reports the estimate and interval and makes no coverage claim either way.
Secondary, read the same way and descriptive: Delta_R (restated), Delta_G of S-P4 beside Delta_L, Delta_L per seed, over all five networks, and on logistic regression; the same differences in action coverage.

## 6 Matched three-disease comparison (NHANES diabetes arm, new run)

Diabetes on pooled NHANES 2017–2020 and 2021–2023, set up as the CKD and HTN domains:
- Sample: the same cycles, raw files and recoders as A0-CKD and A0-HTN (`load_cycle` and `build_cycle` of the nhanes-diabetes repository at its current commit, extra tables TCHOL and KIQ_U read from `data_q1/nhanes_raw/`); adults aged 20 or older, examined (RIDSTATR = 2), not pregnant, label available, complete cases on the 16 features.
- Label (the rule the dependency-graph study NHANES diabetes tables already use, not a new one): primary HbA1c ≥ 6.5% (LBXGH, the dependency-graph study "HbA1c" label); secondary, refit: told by a doctor that they have diabetes (DIQ010 = 1; borderline = 0; the dependency-graph study "diagnosis" label, `Diabetes_self`). Fasting glucose and medication are not used, because the dependency-graph study tables did not use them as labels.
- Features (16): HighBP, HighChol, BMI, Smoker, PhysActivity, GenHlth, MentHlth, Stroke, HeartDiseaseorAttack, KidneyDisease, Age, Sex, Education, Income, AnyHealthcare, Cycle. This is the HTN schema with Diabetes (DIQ010, the outcome concept, excluded by rule R-OUT) replaced by HighBP. HighBP = told high blood pressure (BPQ020 = 1), a diagnosis history; HighChol = measured total cholesterol ≥ 240 mg/dL (LBXTC), as in CKD and HTN; Smoker = current smoking (SMQ020 and SMQ040), as in CKD and HTN; KidneyDisease = KIQ022; BMI integer.
- Roles derived by the same rule as A0-HTN from the dependency-graph study KG export: BMI, Smoker, PhysActivity levers (inherited from the ADA diabetes roles); HighChol treatable (measured clinical risk factor); HighBP (BPQ020) a new concept HYPERTENSION_DIAGNOSIS_HISTORY, diagnosis history, immutable; GenHlth, MentHlth indicators; all other features immutable; rule R-IMM: Income, Education and AnyHealthcare immutable in every mode. Lock set {GenHlth, MentHlth}. The role table and lock set are written and hashed before the model is fitted.
- Model and generator: the taxonomy study XGBoost configuration, 80/20 stratified split with seed 42, cohort = test patients with p ≥ 0.5, at most the 200 highest-risk (floor 50), DiCE random through the taxonomy study runner in published and lock modes, 5 counterfactuals per patient and seed, generator seeds 42, 123, 2024, 7, 31337; code path copied from `a2_htn_runs.py`. No route-aware, exhaustive or second-authority run (the comparison needs none).
- Outcomes (each computed by the frozen A2 code: `a2_domain` statistics, bootstrap seed 20261111): test AUC; eligible and cohort size; share flippable by one non-indicator feature; O-A1 fully unactionable (action = lever or treatable of this domain); the no-action share (non-empty change set without a lever or treatable, over all returned counterfactuals); O-A2 movability null (100,000 draws); O-A3 valid among requested, lock minus published; lock coverage; share of counterfactuals changing BMI; XGBoost gain of BMI and the indicators. The H1 and H2 decision rules are applied descriptively.
- Secondary variants (same code): `dm_diag` (DIQ010 label, refit); `dm_hbp_measured` (HbA1c label, HighBP replaced by the CKD definition, mean systolic pressure ≥ 130 mmHg, role treatable, refit), so that the diabetes arm can also be read with exactly the CKD feature definitions.
- Matched table: diabetes (this arm), CKD with the socio-economic features frozen (S-P1) and HTN main, each with prevalence, test AUC, cohort, single non-indicator flip share, no-action share, O-A1, movability p, O-A3 and lock coverage. Prevalence and AUC differ between the three; differences in the no-action share are described, not tested, and are not attributed to the disease alone.

## 7 Environment, code and outputs

- the CARLA environment venv for Wachter and the table build, the taxonomy study venv for the diabetes XGBoost and DiCE runs (as CKD C12), `python -I`, below-normal priority, at most two heavy processes, OMP_NUM_THREADS not set.
- Code: `<local path>` (`v5_reclass.py`, `v5_fl_levers.py`, `v5_fl_analysis.py`, `v5_dm_a0.py`, `v5_dm_runs.py`, `v5_dm_analysis.py`), importing the frozen modules unchanged; hashed into the manifest before the first run. A fix after the first run is logged as an engineering entry with a new hash.
- Outputs: `outputs/q1_posthoc_v5/` (reclass, wachter_*, nhanes_dm, analysis). Numbers truncated to 4 decimals, never rounded.
