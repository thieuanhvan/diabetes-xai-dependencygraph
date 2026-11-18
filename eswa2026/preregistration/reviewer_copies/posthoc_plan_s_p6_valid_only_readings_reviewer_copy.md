# Post-hoc plan S-P6: valid-only denominator and two further action readings

POST HOC (S-P6), exploratory, recount of stored outputs, no new run.

Written 18/11/2026 09:08 (machine time), before any recount. The plan is frozen by its SHA-256 in `PLAN_SHA256.txt` next to the script `q1_posthoc_s_p6/s_p6_recount.py`; the script stops if the hash differs.

## 1. Trigger

An external pre-submission review of manuscript ESWA v8 (18/11/2026) raised two points:

- R1.2: the no-action share is computed over all returned counterfactuals, valid or not.
- R1.1: BMI is a state, not a behaviour, and Smoker in the diabetes surveys records ever having smoked 100 cigarettes.

All results of the article had been seen when this plan was written, so S-P6 is exploratory. No generator, model, cohort or split is rerun.

## 2. Recounts

### (A) Denominator restricted to valid outputs

Output sets whose published shares use all returned counterfactuals:

1. DiCE random with XGBoost, logistic regression and random forest, on the seven diabetes datasets (BRFSS 2021, NHIS 2022 and 2024, NHANES 2017–2020 and 2021–2023 under the diagnosis and HbA1c labels).
2. DiCE genetic with XGBoost, on the same datasets.
3. Exhaustive search with XGBoost, logistic regression and random forest, on the same datasets.
4. CKD:
   - main cohort, pre-specified;
   - less-exposed cohort;
   - S-P1, socio-economic features frozen;
   - S-P2, splits 11, 22, 33, 44 and 55, where stored.
5. Hypertension main cohort.
6. The matched NHANES diabetes arm: HbA1c label, diagnosis label, and measured blood pressure.

Each set is computed in published mode and in indicator-lock mode.

For each set, under the published reading or readings:

- Readings:
  - diabetes surveys: the pre-specified reading (lever or treatable) and R5;
  - CKD, hypertension and the matched arm: the graph roles of the domain role table.
- Metrics: no-action share and fully-unactionable share.
- Two denominators:
  - **all returned** (as published): a patient mean over cohort patients with at least one returned output;
  - **valid only**: a patient mean over patients with at least one valid output, counting valid outputs only.
- Also reported: the number of patients and of outputs under each denominator.

Reproduction check. The all-returned values recomputed from the same files must equal the published numbers:

- `outputs/q1_posthoc_v5/reclass/reclass_r5_table.csv` for the diabetes rows;
- `outputs/q1_posthoc_v5/analysis/matched_three_disease.json` for the matched no-action estimates.

Tolerance is 1e-4 after truncation. A mismatch stops the script and is reported. CKD main pre-specified has no stored no-action value in a results file, so it is checked against the manuscript value 30.29% (truncated).

Exhaustive search keeps only valid change sets, so (A) cannot change it; it is reported to confirm this.

Extension-B generators already compute their shares over valid or kept outputs (`v5_reclass.py`, `b_analysis` convention): Actionable Recourse under both costs, Growing Spheres, Wachter on logistic regression and on the five networks, and MINT. They are not recounted. The plan records that, as a result, the Table 6 columns of the manuscript mix denominators: DiCE random over all returned, the other generators over valid or kept outputs.

### (B) Reading R6, diabetes surveys only

R6 is R5 without Smoker. The action features are BMI, PhysActivity, Fruits, Veggies and HvyAlcoholConsump; on NHIS and NHANES only BMI and PhysActivity remain.

Reason: in the harmonised diabetes tables (Supplementary Table S4), Smoker records ever having smoked 100 cigarettes. A change from 1 to 0 is therefore not cessation, which is the same logic R5 applies to the diagnosis flags.

In CKD, hypertension and the matched arm, Smoker is current smoking (SMQ020 and SMQ040) and stays an action, so R6 does not apply there.

### (C) Reading NB: BMI not an action

BMI is removed from the action set in every domain:

- diabetes surveys: R5 minus BMI (NB-R5) and R6 minus BMI (NB-R6);
- CKD, hypertension and the matched arm: the graph roles minus BMI.

NB is descriptive only and changes no graph role.

For the forced-lever comparison (Wachter on networks 46, 48 and 49), FL-L forces BMI as one of its six behaviours, so NB cannot be applied by rerunning. From the stored kept outputs we recount only the action coverage under R5 and under NB-R5: patients with at least one kept output that changes an action feature. This is done for:

- route-aware: `q1_ext_b_posthoc/wachter_mlp_s*/kept_route.csv`;
- FL-L: `q1_posthoc_v5/wachter_mlp_s*/kept_levers.csv`.

Both are pooled over the 600 seed–patient units. No coverage difference is re-estimated.

## 3. Intervals

Headline rows get patient-bootstrap 95% percentile intervals: 2,000 resamples of patients, `numpy.random.default_rng(20261118)`, one generator per row, with patients resampled from those entering the denominator. The headline rows are:

- the Table 4 configurations (DiCE random, XGBoost, seven diabetes datasets, published mode);
- CKD main, pre-specified;
- CKD S-P1;
- hypertension main;
- the matched diabetes rows (HbA1c and diagnosis labels).

All numbers are truncated to four decimals, never rounded.

## 4. Reading rule, fixed before running

A main-text claim is flagged for revision if either condition holds:

- (i) under (A), any headline no-action share moves by 5 percentage points or more (absolute) between the all-returned and valid-only denominators;
- (ii) an ordering stated in the text reverses under (A), or under (B) or (C) where noted below.

The orderings checked:

| Ordering | Readings checked |
|---|---|
| Matched data: diabetes and CKD close, hypertension rare (15.36% / 13.51% / 1.87%) | (A); (C), descriptive |
| Actionable Recourse: range-scaled L1 cost above native cost (73.00% vs 3.20% fully unactionable) | not recounted, valid-based already |
| Growing Spheres: pre-specified reading below R5 | not recounted, valid-based already |
| DiCE genetic touches indicators more than DiCE random | (A) |
| The pre-specified reading gives a lower no-action share than R5 on every diabetes configuration | (A) |

(B) and (C) are sensitivity readings. In advance, they bear on:

- the 26.18–62.09% range (Abstract, 4.1, 5.1), for (B) and (C);
- the matched 15.36 / 13.51 / 1.87% comparison and the sentence that BMI carries almost every hypertension counterfactual (4.5, 5.1, Conclusion), for (C);
- the action coverage behind Δ_L, route-aware versus FL-L (4.8, Abstract), for (C), recount only.

A change of 5 percentage points or more under (B) or (C) is reported, not treated as a revision trigger. The only exception is a reversed ordering under (C) in the matched comparison, which is flagged.

## 5. Outputs

- `outputs/q1_posthoc_s_p6/recount_s_p6.json` and `recount_s_p6.csv`.
- Result note in Vietnamese: `reviews/s_p6_recount_result_vi.md`.
- New deviation row S-P6 (Supplementary Table S15).

The artefact bundle `SHA256SUMS.txt` must be regenerated before submission.
