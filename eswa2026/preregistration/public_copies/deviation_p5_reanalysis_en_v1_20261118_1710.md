# Deviation D-P5: re-analysis on the shared P5 dataset (manuscript v10)

Machine time when written: 18/11/2026 17:10. This note is a new file. The protocol (prereg v3), the hypertension addendum, the six post-hoc plans, the deviation log and MANIFEST_sha256.txt are not edited; their hashes still hold.

## What changed

Every analysis input that the shared dataset P5 (UDSS-MD 0.2.1, to be renamed HCDD; repository commit 3b1809f; NHANES file SHA-256 580d0114…51163e6, BRFSS file SHA-256 7bbfbf0a…27953d9) can supply is now read from P5 instead of from the P7 harmonisation scripts. The P7 filters (age at least 20, examined, not pregnant, label present, complete cases) and the P7 feature coding are applied by `<local>/p7_from_p5.py`. All other code, model settings, seeds, roles, lock sets, graphs, readings, test rules and thresholds are those of v9.

| Input | v9 source | v10 source | Cells that differ |
|---|---|---|---|
| NHANES PhysActivity (all NHANES frames) | 2017–2020: vigorous work activity (PAQ605); 2021–2023: at least 150 min leisure-time activity per week | P5 `pa_meets_guideline` (at least 150 min per week of moderate-equivalent activity) in both cycles | 2017–2020 only; agreement 59.89% in the CKD frame (share coded 1: 26.27% in v9, 34.48% in P5) |
| NHANES MentHlth | PHQ-9 bands, prorated when at least 6 of 9 items answered | P5 `phq9_score` bands (all 9 items required) | values equal where all 9 items answered; 14–75 more missing records per frame |
| NHANES Education | DMDEDUC2 mapped to five EDUCA levels | P5 four levels (DMDEDUC2 1 and 2 merged); the merged level is coded as EDUCA 3 | 131–954 records per frame |
| NHANES HeartDiseaseorAttack | coded 0 when one item is "no" and the other missing | P5 `chd_mi_self`, coded 0 only when both items are "no" | 2 cells (matched diabetes frame) |
| NHANES hypertension label | at least two readings per measure; diastolic 0 counted as a reading | P5 `hypertension_measured_acc` (at least one reading; diastolic 0 missing) | no disagreement on shared records; 9 more labelled records |
| BRFSS 2021 Sex | P4 file (Kaggle derivation; equals the calculated `_SEX`) | P5 `SEXVAR` (the core "sex of respondent" item) | 231 of 236,378 records (0.0977%) |
| NHIS 2022 and 2024 | P7 harmonisation | unchanged (NHIS is not in P5 0.2.1) | none; NHIS results of v9 are kept |

Frame sizes: CKD 9,837 to 9,793; hypertension 9,944 to 9,905; matched diabetes 10,353 to 10,300 (HbA1c label); Table 4 NHANES 2017–2020 6,409 to 6,389 and 2021–2023 4,312 to 4,279; BRFSS 236,378 unchanged.

BRFSS Sex. The BRFSS 2021 codebook defines `SEXVAR` as the sex of respondent from the core questionnaire and `_SEX` as a calculated variable that, in states using the optional sexual orientation and gender identity module, takes the birth sex reported there. v9 described Sex as "the binary sex variable each survey records from the respondent's report"; `SEXVAR` matches that description and matches the NHANES (RIAGENDR) and NHIS (SEX_A) items. The choice was made from the codebook before any BRFSS model was refitted on the P5 frame.

## Why

v9 §3.4 disclosed that NHANES PhysActivity measured different constructs in the two cycles. The shared dataset P5 defines one physical-activity construct for both cycles, and the author decided that P7 should read its data from P5 so that P7 and the later papers that use P5 rest on one data definition. The other differences in the table come with that decision; they were not chosen one by one.

## Results seen at the time

Yes. The decision (author, 18/11/2026 about 14:30) was taken after a measurement run on P5 0.2.0 (report `<local>/p5_migration_report_vi.md`, 13:50) had shown how the headline numbers change, including that CKD H3 moves from "supported (equivalent)" to "undecided". The NHANES frames of 0.2.1 are byte-identical to those of 0.2.0, so the v10 CKD, hypertension and matched-diabetes results equal the measurement run.

## Handling

- The v10 manuscript reports the P5 results as the main results, under the pre-specified rules without change.
- The v9 results (P7 coding) are reported beside them as a sensitivity analysis, for every hypothesis and every headline number; nothing from v9 is dropped.
- The measurement run also had a third variant, P5 with the v9 PhysActivity coding. It is not used as the main analysis, because the decision concerned the data source as a whole. Its hypothesis verdicts are recorded here so that the choice can be checked: CKD H1 supported, H2 supported, H3 supported (equivalent; 0.01952, 98% interval [0.003236, 0.04354]); S-P1 H1 supported (p = 0.008929), H2 not supported (coverage 0.9479), H3 undecided.
- Post-hoc analyses keep their plans; seeds fixed by number in the plans (S-P4 key networks 46, 48, 49) are kept even if the seed screen on the new data accepts different networks, and any such difference is reported.

## Hypotheses, v10 (P5) against v9 (P7 coding)

| Test | v10 (P5) | v9 |
|---|---|---|
| CKD H1 | supported (0.2097, lower 0.1787; p = 0.0003399) | supported (0.2102, lower 0.1819; p = 0.003689) |
| CKD H2 | supported (Δ 0.05740, lower 0.03073; coverage 0.9943) | supported (Δ 0.07191, lower 0.04233; coverage 0.9893) |
| CKD H3 | undecided (0.03800 [0.01257, 0.06749]) | supported, equivalent (0.008382 [0.001034, 0.01762]) |
| H1-HTN | not supported (no action 0.02450, upper 0.04000; p = 1.000) | not supported (0.01879, upper 0.03300; p = 1.000) |
| H2-HTN | not supported (Δ −0.05020, lower −0.08860; coverage 0.7300) | not supported (Δ −0.02060, lower −0.05320; coverage 0.8500) |
| H3-HTN, H4, H5 | not reached (unchanged reasons) | not reached |

Numbers are truncated to four significant digits. The CKD secondary cohort, the post-hoc analyses and the diabetes tables are compared in the v10 supplement.

## Addendum (18/11/2026 22:39): post-hoc analyses on P5

The seed screen of B-P1 on the P5 BRFSS frame accepted the same five seeds as in v9 (44, 45, 46, 48 and 49); seed 42 again gave the constant network of B-E2. The S-P4 key networks 46, 48 and 49 are therefore the networks where the lock fails on both data versions (lock coverage 1, 0 and 1 of 200 in v10). Over the five further CKD splits (S-P2), H1 and H2 hold in every split and H3 is undecided in every split (v9: equivalent in split 33).
