# Pre-registration addendum: a third domain, hypertension (HTN), for the P7 Q1 extension (v1)

Version v1, written 12/11/2026 from 07:39 (machine time, checked with `date`). It adds a third disease domain to the frozen pre-registration `prereg_q1_extension_en_v3_20261111_1645.md` (SHA-256 95a83da5…112369d, "v3" below). v3 is not edited. Where this addendum is silent, v3 and the clarifications C1–C14 of `deviations_log_q1_en.md` apply to the HTN domain as they apply to CKD.

Author of the plan: Claude (Anthropic), for Van Thieu. The addendum goes to a blind review before any HTN extraction or model fit. Changes made in answer to that review, before any extraction output or model exists, give a v2 of this addendum and are not deviations.

## 0 Status at writing and what the author had seen

Nothing HTN-specific had been extracted, fitted or generated. Declarations:

1. **CKD results.** Before writing, the author read the CKD A2 results note (`outputs/q1_domain_ckd/a2_analysis/a2_results_note_en.md`) and the KDIGO agreement file. CKD main cohort: H1 supported (O-A1 0.2102, movability-null p = 0.0036), H2 supported, H3 supported (O-A5 0.0083); less-exposed cohort: H1 undecided (p = 0.0146). KDIGO agreed graph: BMI to GenHlth, PhysActivity to MentHlth, BMI to HighBP, BMI to HighChol (κ 0.9169 over 88 Concept pairs). The thresholds below are copied from v3 and were not changed after reading these numbers.
2. **HTN data.** The NHANES HTN table (Section 4) was built before this addendum was written. The author saw flow counts, label prevalence per cycle and missingness, and nothing else: no association between any feature and the label, no model.
3. **Guideline text.** No text of the 2025 AHA/ACC guideline was read. The PDF could not be fetched (Section 2), so the unit-selection rule (Section 5.1) was written without seeing the guideline's headings, wording or page layout. No keyword check of the kind declared in v3 Section 0 item 2 was made.
4. **Prompts.** The two extraction prompts are the frozen CKD prompts, reused byte for byte. Nothing was written or tuned for this guideline.

## 1 Purpose and scope

Question: does the result of the CKD domain hold for a third guideline and disease? That is, with roles derived mechanically from the graph, do generators place changes on survey health-status indicators beyond what movability explains, and does the graph-derived lock remove this cheaply (H1-HTN, H2-HTN)? Is route-aware enforcement with routes from the hypertension guideline equivalent to the lock (H3-HTN)?

In scope: guideline choice, NHANES HTN data, role table, extraction design, hypotheses and their tests. Out of scope as in v3 Section 1: human raters, manual annotation, longitudinal validation.

What HTN adds over CKD: a label that is a measured physiological state with high prevalence, and a domain in which the main treatable concept of the earlier domains (blood pressure) becomes the outcome. The second point tests whether the role derivation handles a Concept that changes from feature to outcome.

## 2 Guideline, how it was sought, and the secondary authority

### 2.1 Primary guideline

**Chosen:** the 2025 AHA/ACC/AANP/AAPA/ABC/ACCP/ACPM/AGS/AMA/ASPC/NMA/PCNA/SGIM Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults (Jones DW, Ferdinand KC, Taler SJ, et al.). It was published simultaneously in three journals. Crossref records (checked 12/11/2026, generic client, no e-mail):

| Copy | DOI | Crossref licence record |
|---|---|---|
| JACC 2025;86(18):1567–1678 | [10.1016/j.jacc.2025.05.007](https://doi.org/10.1016/j.jacc.2025.05.007) | version of record: Elsevier user license (`elsevier.com/open-access/userlicense/1.0`); TDM: Elsevier TDM licence |
| Hypertension 2025;82(10) | [10.1161/HYP.0000000000000249](https://doi.org/10.1161/HYP.0000000000000249) | none |
| Circulation 2025;152(11) | [10.1161/CIR.0000000000001356](https://doi.org/10.1161/CIR.0000000000001356) | none |

**Copy used: JACC.** It is the only copy with a stated reuse licence. The Elsevier user license permits access, download, copying and text and data mining for non-commercial purposes and forbids redistribution and adaptation. It is free to read, but it is not a Creative Commons open-access licence. The guideline is not deposited in PubMed Central (Europe PMC: "subscription required" for all three DOIs).

**How it was sought.** One automated request each to the publisher PDF links of the JACC, Hypertension and Circulation copies and of the 2017 fallback ([10.1161/HYP.0000000000000065](https://doi.org/10.1161/HYP.0000000000000065)) (curl, one request each, standard browser user-agent string) returned HTTP 403 from bot protection. A further request to the ScienceDirect PDF link was stopped by the session's permission check before it was sent. No login, no retry and no other route was attempted. **The PDF must be downloaded by hand by anh Vân** from the JACC article page and saved as `paper7/references/q1_htn/AHA-ACC-2025-HBP-Guideline_JACC.pdf`. Its SHA-256, size, page count, download date and URL then go into `references/q1_htn/README.md` and the A0-HTN manifest, before any text conversion is read.

**Fallback.** The 2017 ACC/AHA guideline is used only if the 2025 guideline cannot be obtained by hand. That would be a deviation. The 2017 copy is equally blocked to automated requests and carries no Crossref licence record, so it has no advantage.

### 2.2 Licence and use

- **(a) Automated extraction.** Permitted by the Elsevier user license for non-commercial purposes. No statutory text-and-data-mining exception is relied on.
- **(b) Sending text to Claude.** Same reasoning as v3 Section 4.3 (b): the purpose is non-commercial academic research; an API or agent session processing the text on the licensee's behalf is part of the licensee's own use and not a public sharing. The text is sent with its attribution and licence notice.
- **(c) Release.** The released KG carries no verbatim AHA/ACC text, only locator, strength, class and level of evidence, and an own-words paraphrase, as for ADA and KDIGO. The PDF, its text conversions, units, chunks and rendered prompts are not redistributed (the licence forbids redistribution) and are not pushed to any repository.

### 2.3 Secondary authority for cross-guideline agreement

**Decision: KDIGO 2024 is the secondary authority for A-Q4-HTN. ADA 2026 is an additional comparison.**

Reasons:

1. The KDIGO graph was built with the same protocol the AHA/ACC graph will use: two extractors, the same 12-Concept vocabulary, the same quotation check and the intersection rule. A disagreement between AHA/ACC and KDIGO verdicts then reflects the guidelines rather than two different ways of building edges. The ADA edges (`depgraph/edges.py`) were coded by one author from numbered recommendations, without quotation check or a second extractor.
2. KDIGO treats blood-pressure control and lifestyle in dedicated sections (§3.2–3.4), so it addresses the same levers.
3. ADA cannot be re-extracted under the HTN protocol, because its terms of use exclude automated extraction (v3 Section 12).

Limitations, stated now: KDIGO addresses people with CKD. Its edges are read without population scope in A-Q4-HTN. Only 371 of 9,944 HTN participants report kidney disease. The ADA comparison is reported beside it with the same statistics and the same reading rule. Neither comparison is primary.

## 3 Domain, roles and lock set

**Derivation.** v3 Section 3 steps 1–4, run by `a0_role_table_htn.py`: each HTN Variable follows `measures` to its Concept; a Concept with a diabetes-domain RoleAssignment inherits role and direction; a new Concept gets its role from the fixed rule. Two domain rules are added and applied by the same script:

- **R-OUT.** The Concept measured by the outcome (BLOOD_PRESSURE) is the domain outcome. It is not a feature and has no role in the HTN domain. HighBP is removed from the feature set.
- **R-IMM.** Every feature whose role is immutable has direction immutable, in every generator mode (published, lock, route-aware; DiCE and exhaustive search). Income, Education and AnyHealthcare were movable upward in CKD under the P4 direction rules. A review flagged this as a flaw: a recourse that raises income or buys insurance is not a health action. In HTN they are frozen.

**Role table** (SHA-256 f1a6b6d1…876a94302; lock set 78c013db…431ea0095; identical to the CKD lock set):

| Feature | Concept | NHANES source | Role | Direction | How derived |
|---|---|---|---|---|---|
| Diabetes | DIABETES_HISTORY | `DIQ010` = 1 | immutable | immutable | new Concept, rule: diagnosis history |
| HighChol | CHOLESTEROL | `LBXTC` ≥ 240 mg/dL (measured) | treatable | down | inherited |
| BMI | BODY_WEIGHT | `BMXBMI`, integer | lever | bidirectional | inherited |
| Smoker | SMOKING | `SMQ020` = 1 and `SMQ040` in {1, 2} | lever | down | inherited |
| PhysActivity | PHYSICAL_ACTIVITY | 2017–2020 `PAQ605`; 2021–2023 `PAD790Q/U`–`PAD820`, moderate + 2 × vigorous ≥ 150 min/week (corrected rule, O1-res) | lever | up | inherited |
| GenHlth | GENERAL_HEALTH | `HUQ010` | indicator | down | inherited |
| MentHlth | MENTAL_HEALTH | PHQ-9 total in P7 bands | indicator | down | inherited |
| Stroke | STROKE_HISTORY | `MCQ160F` | immutable | immutable | inherited |
| HeartDiseaseorAttack | CHD_MI_HISTORY | `MCQ160C` or `MCQ160E` | immutable | immutable | inherited |
| KidneyDisease | KIDNEY_DISEASE_HISTORY | `KIQ022` = 1 | immutable | immutable | new Concept, rule: diagnosis history |
| Age, Sex | AGE, SEX | `RIDAGEYR`, `RIAGENDR` | immutable | immutable | inherited |
| Education, Income, AnyHealthcare | EDUCATION, INCOME, HEALTH_COVERAGE | `DMDEDUC2`, `INDFMPIR` (5 bands), `HIQ011` | immutable | immutable | inherited role; R-IMM sets direction |
| Cycle | SURVEY_CYCLE | 0 = 2017–2020, 1 = 2021–2023 | immutable | immutable | new Concept, rule: survey design |

Proxy items: the code has no separate proxy role (v3 Section 2). Proxies are immutable. In HTN the proxy-type items are the diagnosis histories (Diabetes, KidneyDisease, Stroke, HeartDiseaseorAttack). They are downstream of or associated with blood pressure, so they carry outcome information but cannot be acted on.

**Lock set:** {GenHlth, MentHlth}. **Movable set for the null:** {HighChol, BMI, Smoker, PhysActivity, GenHlth, MentHlth}. A patient has at most two movable indicators, so the exact null for one patient has at most C(6, 2) = 15 subsets.

**Diabetes and CKD as conditions.** Both are kept as immutable diagnosis-history features. Reasons: the recourse question is what a person can change, and neither a diagnosis nor its history is an action; hypertension guidelines treat both as conditions that modify management. CKD enters as the self-reported item `KIQ022`, not as the measured eGFR/ACR label of the CKD domain. The measured label would need laboratory completeness, which removes participants, and it is partly a consequence of blood pressure. The borderline coding of `DIQ010` is a sensitivity analysis, as in CKD.

**Role-conflict check.** As v3 Section 3 step 5: any agreed AHA/ACC statement that recommends a direct clinical intervention on GenHlth or MentHlth Concepts is listed; the primary analysis keeps the inherited role; a sensitivity reading re-labels that Concept as treatable.

## 4 Data, cohort and labels (A0-HTN, built 12/11/2026)

**Source and code.** NHANES 2017–2020 (`P_` files) and 2021–2023 (`_L` files), the same raw files and recoders as the CKD table (nhanes-diabetes commit 778be1a, which contains the corrected PhysActivity rule). Script `a0_nhanes_htn.py`; check: the rebuilt P7 features equal P7's NHANES tables (0 mismatches on 14 features, 8,702 and 6,185 rows).

**Analytic sample**, in this order: (1) age ≥ 20; (2) examined at the MEC, `RIDSTATR` = 2; (3) not pregnant, `RIDEXPRG` ≠ 1; (4) primary label available; (5) complete cases on all 16 features.

**Primary label L1 (measured hypertension).**

- Readings: oscillometric `BPXOSY1`–`BPXOSY3` and `BPXODI1`–`BPXODI3` (`P_BPXO`, `BPXO_L`). Mean of the available readings, with at least two valid readings for each of systolic and diastolic pressure. The ACC/AHA guidelines define BP status from the average of two or more readings.
- Positive if mean systolic ≥ 130 or mean diastolic ≥ 80 mmHg (stage 1 or higher in the ACC/AHA classification, the same thresholds in 2017 and 2025). Negative only if both means are available and both are below. Missing otherwise.
- What the label is: elevated measured BP at one examination. It is not a diagnosis, which needs readings on two or more occasions. A treated participant whose BP is controlled is labelled negative. The model detects current state, not risk.

**Secondary label L2 (measured or treated).** L1 positive, or now taking prescribed medicine for high blood pressure (2017–2020 `BPQ050A` = 1; 2021–2023 `BPQ150` = 1). Negative if L1 is negative and medication use is known to be no (`BPQ020` = 2, `BPQ040A` = 2 in 2017–2020, or the "now taking" item = 2). Missing otherwise. Both medication items are asked only of people told they have high BP, so L2 also uses self-report. L2 is used in a secondary refit (Section 7.4).

**Less-exposed cohort.** As the CKD `KIQ022` rule: participants ever told by a doctor that they have high blood pressure (`BPQ020` = 1) are removed from the cohort, with the same fitted model and the same cohort rule (clarification C10; missing `BPQ020` counted as not told). These people are aware of their status and most are treated, so recourse means something different for them. H1-HTN to H3-HTN outcomes are re-estimated there as secondary.

**Counts** (analytic sample; shares truncated to four decimals; `outputs/q1_domain_htn/a0_nhanes_htn/nhanes_htn_flow.md`):

| | 2017–2020 | 2021–2023 | Pooled |
|---|---|---|---|
| after steps 1–3 | 8,457 | 6,023 | 14,480 |
| L1 missing (fewer than 2 readings) | 895 | 205 | 1,100 |
| L1 available | 7,562 | 5,818 | 13,380 |
| analytic sample (complete cases) | 5,887 | 4,057 | 9,944 |
| L1 positive | 2,588 (0.4396) | 1,675 (0.4128) | 4,263 (0.4287) |
| L2 positive / available | 3,279 / 5,885 (0.5571) | 2,210 / 4,056 (0.5448) | 5,489 / 9,941 (0.5521) |
| told high BP (`BPQ020` = 1) | 2,263 (0.3844) | 1,488 (0.3667) | 3,751 (0.3772) |
| less-exposed sample | 3,624 | 2,569 | 6,193 |
| L1 prevalence in less-exposed sample | 0.3283 | 0.3188 | 0.3243 |

**Missingness** among label-available participants (step 4): Income 0.1288 and 0.1289; MentHlth 0.0428 and 0.1158; HighChol 0.0637 and 0.0904; all other features below 0.01. Any feature missing: 0.2215 (2017–2020) and 0.3026 (2021–2023). Complete-case analysis as in P7 and CKD; no imputation.

**Survey weights.** Not used, as v3 Section 4.5. Weighted refit as sensitivity (`WTMECPRP`, `WTMEC2YR`).

**Hashes.** Analytic table e8efa0d3…44642718; flow (md) 7b107476…582d51873; flow (json) df3f6399…c041d9d5 (full values in the A0-HTN manifest).

## 5 Extraction design

### 5.1 Units

The section list cannot be written by hand without reading the guideline. It is therefore a rule, frozen now in `section_rule_htn_v1.json` and applied by `a0_build_chunks_htn.py`:

- Main body only: from the first numbered section to the reference list. Excluded: front matter (abstract, contents, take-home messages, preamble), any front-matter summary that repeats body recommendations, references, appendices.
- A numbered heading (any level) whose title contains one of these keywords defines a unit, together with its subsections:
  - levers and behaviours: nonpharmacolog, non-pharmacolog, lifestyle, weight, obes, diet, nutrition, sodium, potassium, physical activity, exercise, fitness, alcohol, tobacco, smoking, nicotine, stress, sleep;
  - health status: quality of life, well-being, wellbeing, depress, mental health, psycholog, cognit, dementia, brain health, functional, patient-reported.
- A table or figure whose caption matches is also a unit, cut from the `-layout` text (as CKD clarification C2).
- The detected heading index must agree with the printed table of contents. Differences are resolved by the printed contents. That resolution, the footer and header regexes and the body limits are logged as clarifications before any extraction.
- If no heading matches, the graph is empty (degenerate) and no section is added by hand.

Over-inclusion (for example a drug section whose heading contains "potassium") costs only tokens, because both prompts exclude drug sources. A smoke test of the script on the KDIGO text confirmed that it runs and showed this case.

Declared limitation: routes stated only under headings with no keyword are not extracted. CKD also used a closed section list.

### 5.2 Chunking

Identical to CKD: unit-level chunks of at most 6,000 tokens, 500-token overlap, line-snapped, Qwen2.5 GGUF vocabulary through llama.cpp b12283 `/tokenize` (tokeniser only, no generation; clarification C1). The same chunk files go to both extractors.

### 5.3 Extractors

Both extractors are Claude sessions (model id `claude-opus-5-5`). The design does not have two model families, and the paper says so.

- **Extractor A:** frozen CKD prompt v1 (system 2959ef9d…; user template 960a8261…).
- **Extractor B:** frozen CKD prompt v2 (system 3a38d58b…; user template 8e9c4a25…). v2 was written without opening v1 (event E1), so the two prompts were written independently. Their independence is in the wording, not in the model.
- Vocabulary: the frozen 12-Concept list (`concepts_constructs_v1.json`, 6db9963a…), unchanged. HTN Concept-to-item map: `concepts_constructs_htn_v1.json`. Edges with BLOOD_PRESSURE at either end are kept in the KG as routes to the outcome but are not used by the audit, and a path through BLOOD_PRESSURE does not count for k = 2.
- Runtime: one fresh sub-agent per chunk and per extractor. It sees only its system prompt and rendered user message, and has no access to the other extractor, the prereg, this addendum, CKD outputs, the role tables or any result. Temperature and output length cannot be controlled (as D2), so run-to-run reproducibility is not claimed; the output files and their hashes are the record.

### 5.4 Recall gate (before any HTN chunk is extracted)

- Both extractors run on the 18 frozen recall-gate chunks of the CKD freeze (WHO HEARTS-D ×3, MoH 5481 ×10, NICE NG28 ×5), hash-checked. Extractor A uses the frozen v1 gate messages; extractor B uses the v2 template filled by `a0_render_gate_prompts_v2.py` (already rendered and hashed).
- Scoring as v3 Section 4.4 and C3. Pass rule, for each extractor separately: recovers the HEARTS-D agreed edge and at least 3 of the 5 MoH 5481 agreed edges after the quotation check. NG28 output is reported as a false-positive count.
- In CKD the Claude prompts were never gate-tested (only the local model was). For HTN both are.
- If either extractor fails, no new prompt is written. The HTN agreed graph is not reached; H3-HTN and A-Q4-HTN are reported as not reached; the passing extractor's graph is described. H1-HTN and H2-HTN do not depend on edges and run unchanged.

### 5.5 Quotation check, agreement gate and graph

- Quotation check: v3 Section 4.4 and C5, on the frozen `-raw` and `-layout` text of the JACC PDF.
- Agreement unit: the 88 candidate Concept pairs (C7). Statistics: Cohen's κ, PABAK, positive and negative agreement; also on the 20 HTN item pairs as secondary.
- **Agreement gate:** κ ≥ 0.40 and positive agreement ≥ 0.50. 0.40 is the lower bound of "moderate" agreement in the Landis–Koch convention; positive agreement guards against κ driven by the many pairs neither extractor finds. Both thresholds are conventions.
- If the gate fails, the intersection graph is built and reported, but H3-HTN is "not testable: agreement gate failed" and A-Q4-HTN is descriptive only. If neither extractor finds any pair, κ is undefined and the graph is degenerate (not a gate failure).
- Graph: the intersection of quotation-checked pairs; union as secondary; agreed strength is the weaker of the two (C8); no person adjudicates.

### 5.6 Grading for evidence-support scores (secondary)

AHA/ACC recommendations carry a Class of Recommendation (COR) and a Level of Evidence (LOE). "Graded" means a recommendation with COR and LOE. Scores: COR 1 with LOE A 0.9; COR 1 with LOE B-R or B-NR 0.7; COR 1 with LOE C-LD or C-EO 0.5; COR 2a or 2b, any LOE, 0.3; table entry or explicit ungraded statement 0.6; narrative 0.2. A COR 3 statement (no benefit or harm) does not support an edge.

## 6 Models, generators, cohort and seeds

- **Split:** stratified 80/20 on L1, seed 42.
- **Primary model:** XGBoost with the P4 configuration, threads unchanged. OMP_NUM_THREADS is not set by any HTN script (lesson of B-E3).
- **Features:** the 16 features of Section 3, in role-table order. P4 ranges as CKD clarification C13 (a); KidneyDisease is added as immutable (0, 1).
- **Cohort:** test patients with predicted probability ≥ 0.5, at most the 200 highest-risk. If fewer than 50 qualify, H1-HTN to H3-HTN are not reached. No patient below 0.5 is ever included.
- **Pre-generator property (S1):** share of cohort patients who can be flipped by one non-indicator change, computed after the fit and before any generator, reported whatever the result.
- **Generators and modes:**
  - DiCE random: published, indicator lock, route-aware (rejection and regeneration with seed + 100,000·r, at most 8 rounds). For H1-HTN and H2-HTN.
  - Exhaustive sparse search (P7): published, lock, route-aware, capped. For H3-HTN and the lock costs.
  - R-IMM holds in every mode: Income, Education and AnyHealthcare never change.
  - DiCE genetic, LR and Random Forest: secondary, as CKD.
- **Route-aware primary reading:** k = 1, 𝒜 = {AHA/ACC 2025}, 𝒮 = all.
- **Seeds:** split 42; generators 42, 123, 2024, 7, 31337; DiCE regeneration seed + 100,000·r; bootstrap, permutation and Monte Carlo 20261111 (same as CKD, so domains are comparable).
- **Compute:** CPU, below-normal priority, at most one heavy process for HTN while other P7 work runs (machine limit two).

## 7 Outcomes and hypotheses

Metric definitions are those of v3 Section 2 and clarifications C9 and C11 (one-sided 99% bounds as 1st/99th bootstrap percentiles; bootstrap resampling per metric with `default_rng(20261111)`; edge cases of coverage, O-share and pairing).

### 7.1 Primary outcomes (pooled NHANES, L1, XGBoost, derived roles)

- **O-A1-HTN:** fully unactionable share, published mode, DiCE random.
- **O-A2-HTN:** per-patient movability null of v3 Section 4.7. M_i is the set of features movable for patient i under R-IMM, at most the six features of Section 3. Exact per-patient enumeration (at most 15 subsets), 100,000 Monte Carlo draws across patients, seed 20261111, p = (1 + #{T* ≥ T}) / 100,001, ties against the hypothesis (C11).
- **O-A3-HTN:** valid among requested, lock minus published, DiCE random, with lock patient coverage.
- **O-A5-HTN:** per-patient difference in normalised L1 distance of the best counterfactual, lock minus route-aware, exhaustive search; can be negative (Lemma 3 is lexicographic).

### 7.2 Hypotheses

| ID | Statement | Decision rule (copied from v3 H1–H3) |
|---|---|---|
| H1-HTN | derived roles reproduce the failure in HTN | (i) replication check: one-sided lower 99% bound of O-A1-HTN > 0.10; and (ii) confirmatory: movability-null p < 0.01. Not supported if the upper bound ≤ 0.10 or p ≥ 0.5; undecided otherwise |
| H2-HTN | the derived lock is cheap | one-sided lower 99% bound of O-A3-HTN > −0.05 and lock coverage (point estimate) ≥ 0.95. Not supported if the upper bound < −0.05 or coverage < 0.95; undecided otherwise |
| H3-HTN | route-aware with AHA/ACC routes is equivalent to the lock | TOST at α = 0.01: 98% percentile bootstrap interval of mean O-A5-HTN inside (−0.05, 0.05) is supported; lower bound ≥ 0.05 or upper bound ≤ −0.05 is not supported; undecided otherwise |

The margin δ = 0.05 keeps the domain-free justification of v3 H3: one GenHlth step is 0.25 on the scaled grid, a binary feature 1, one PHQ-9 band at least 5/30, and 0.05 is about 0.8 BMI units on the P4 range.

### 7.3 Degenerate, near-degenerate and gate cases for H3-HTN

- **Degenerate:** the AHA/ACC intersection graph has no edge from a lever into GenHlth or MentHlth (BLOOD_PRESSURE edges do not count, Section 5.3). Route-aware then equals the lock, and H3-HTN is "not testable: degenerate graph". A-Q4-HTN is still reported.
- **Near-degenerate:** edges into an indicator exist, but every supporting lever is movable for fewer than 10% of cohort patients. Computed from the cohort before any generator runs. H3-HTN is reported with this flag and its equivalence is not counted as evidence about the graph.
- **Gate cases:** recall gate failed gives "not reached" (Section 5.4); agreement gate failed gives "not testable: agreement gate failed" (Section 5.5).

### 7.4 Secondary (95% intervals, exploratory)

- O-A4-HTN, change sizes, capped reading, leakage under all readings, touch share, route-aware cost, exhaustive costs, distinct counterfactuals, local outlier factor, evidence-support scores, Python–SPARQL check (must agree on 100%; a disagreement is a bug).
- Readings: k = 2 permissive and strict; 𝒜 = {AHA/ACC, KDIGO}, {AHA/ACC, KDIGO, ADA}; 𝒜 = {KDIGO}; 𝒜 = {ADA}; graded only (COR and LOE present); in-scope (an edge whose stated population names hypertension or high blood pressure applies only to cohort patients with L1 = 1).
- **A-Q4-HTN (key secondary):** indicator-touching HTN counterfactuals, published mode, DiCE random and exhaustive search, verdicts under 𝒜 = {AHA/ACC} and 𝒜 = {KDIGO} at k = 1; raw agreement and κ with 95% patient-cluster bootstrap intervals; reading rule of v3 (≥ 0.80 carries across, < 0.60 guideline-specific, partial in between). The same comparison against 𝒜 = {ADA} is reported beside it.
- Less-exposed cohort (`BPQ020` = 1 removed); L2 refit (same features, same protocol); per-cycle O-A1-HTN and O-share; 2021–2023-only refit (matched PhysActivity construct); weighted refit; Diabetes borderline coding; role-conflict sensitivity; edge-permutation null (1,000 permutations).
- **CKD-comparable reading:** published-mode DiCE random with Income, Education and AnyHealthcare movable upward as in CKD, to show how much R-IMM changes O-A1 and O-share. Descriptive only.

## 8 Multiplicity

H1-HTN, H2-HTN and H3-HTN form a new family of three, separate from the v3 family of five (different domain, separate claim; no statement pools the two). Each is tested at α = 0.01, the same as v3. This is conservative against Bonferroni for three (0.0167) and keeps the HTN verdicts on the same scale as CKD. H1-HTN is an intersection–union test. Verdict categories as v3 Section 8, plus "not testable: agreement gate failed".

## 9 Expected results, stated before any HTN run

| Hypothesis | Expected | Basis |
|---|---|---|
| H1-HTN (i) | likely pass | CKD O-A1 0.2102 and P7 NHANES 19.07–22.85% with a similar schema. R-IMM removes three movable non-indicators, which may raise the indicator share |
| H1-HTN (ii) | uncertain | CKD main p = 0.0036, less-exposed 0.0146. R-IMM shrinks the null set, which raises the null mean as well |
| H2-HTN | likely pass | CKD and P7 |
| H3-HTN | supported (equivalent) or not testable (degenerate) | CKD O-A5 0.0083. Whether the AHA/ACC sections state routes into general health or depression in the 12-Concept vocabulary is unknown; the guideline text was not read |
| A-Q4-HTN | uncertain | no AHA/ACC edge known |

A further threat: blood pressure strongly depends on age, which is immutable, so the cohort will be older and the share of patients flippable by one non-indicator change may be lower than in CKD.

## 10 Deviations and what counts as one

The rules of v3 Section 9 apply: bugs need a failing test first; scripts are hashed before the first primary run; no exclusion of patients, configurations or seeds because of results; after any primary result, hypotheses and thresholds do not change and any change is post hoc.

For HTN, each of the following, made after this addendum is hashed, is a deviation and goes into `deviations_log_q1_en.md` and main §0x with date, reason and results seen:

- any change to the labels, thresholds, reading rule, cohort or less-exposed rule, feature set or role table (`--check` must report UNCHANGED before the model is fitted);
- any change to the keyword list, heading rule, body limits, chunking rule, prompts, vocabulary, recall gate or agreement gate;
- using the Hypertension or Circulation copy instead of JACC (same content, different page numbers), or the 2017 guideline;
- writing a new prompt after any gate result;
- running any HTN step in another order than: PDF in hand, then index-only stage and logged clarifications, then chunks frozen and appended to the A0-HTN manifest, then recall gate, then extraction, then quotation check and agreement, then model fit, cohort and S1, then near-degenerate check, then generators, then analysis.

Clarifications (implementation choices the addendum leaves open, such as footer regexes or table-of-contents reconciliation) are logged before the step that uses them and are not deviations. Slippage in time is not a deviation.

## 11 Open questions for anh Vân

1. **Download the guideline by hand.** JACC copy, DOI 10.1016/j.jacc.2025.05.007, from jacc.org or ScienceDirect; save as `paper7/references/q1_htn/AHA-ACC-2025-HBP-Guideline_JACC.pdf`. Automated requests were blocked.
2. **Does the Elsevier user license fit?** It permits non-commercial TDM but is not Creative Commons. The plan relies on it as v3 relied on CC BY-NC-ND for KDIGO.
3. **Article structure.** Is HTN a third domain in the same Q1 article (as assumed here) or kept for a later paper? It adds roughly one results table and one flow diagram.
4. **Same-family extractors.** Both extractors are Claude. Accept, or approve a second run of the local model on GPU for HTN, even though it failed the CKD recall gate?
5. **R-IMM in CKD.** HTN freezes Income, Education and AnyHealthcare; the frozen CKD analysis did not. Whether CKD gets a post-hoc R-IMM reading is for the manuscript revision, not this addendum.

## 12 Files and hashes

- Code: `<local>` (synced to `diabetes-xai-dependencygraph/q1/q1_domain_htn/`, code only).
- Outputs: `paper7/outputs/q1_domain_htn/` (`a0_nhanes_htn/`, `a0_role_table/`, `a0_freeze/`).
- Freeze manifest: `outputs/q1_domain_htn/a0_freeze/A0_HTN_MANIFEST_sha256.txt` (stage 1 now; later stages appended, never rewritten). Its hash and this addendum's hash are in `prereg/MANIFEST_sha256.txt`.
- Guideline: `paper7/references/q1_htn/README.md` (status, URL, licence; SHA-256 when the PDF is in hand).

## 13 References

1. Jones DW, Ferdinand KC, Taler SJ, et al. 2025 AHA/ACC/AANP/AAPA/ABC/ACCP/ACPM/AGS/AMA/ASPC/NMA/PCNA/SGIM Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults. J Am Coll Cardiol. 2025;86(18):1567–1678. [https://doi.org/10.1016/j.jacc.2025.05.007](https://doi.org/10.1016/j.jacc.2025.05.007)
2. The same guideline, Hypertension. 2025;82(10). [https://doi.org/10.1161/HYP.0000000000000249](https://doi.org/10.1161/HYP.0000000000000249)
3. Whelton PK, Carey RM, Aronow WS, et al. 2017 ACC/AHA/AAPA/ABC/ACPM/AGS/APhA/ASH/ASPC/NMA/PCNA Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults. Hypertension. 2018;71(6):e13–e115. [https://doi.org/10.1161/HYP.0000000000000065](https://doi.org/10.1161/HYP.0000000000000065)
4. KDIGO CKD Work Group. KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease. Kidney Int. 2024;105(4S):S117–S314. [https://doi.org/10.1016/j.kint.2023.10.018](https://doi.org/10.1016/j.kint.2023.10.018)
5. Landis JR, Koch GG. The measurement of observer agreement for categorical data. Biometrics. 1977;33(1):159–174. [https://doi.org/10.2307/2529310](https://doi.org/10.2307/2529310)

**Verification.** DOIs 1–3 and 5 were checked with the Crossref API on 12/11/2026; DOI 4 on 11/11/2026 (v3).
