# Pre-registration: extensions of P7 for a Q1 journal (v3, final design)

*A guideline-derived dependency graph, represented as a knowledge graph, as an audit and derivation instrument for counterfactual recourse: a second guideline and disease with a measured outcome, further generator–model pairs, and a formal account of indicator leakage*

Version v3, written 11/11/2026 16:38 (machine time, checked with `date`). It is the last design revision. After it, only a check that the listed fixes were made, and then the runs.

It replaces:

- v2 (16:23, SHA-256 c22032b8…37559bb8), reviewed in `prereg/blind_review_prereg_q1_v2_20261111_1632.md` with the verdict MAJOR REVISION BEFORE RUNNING;
- v1 (16:08), reviewed in `prereg/blind_review_prereg_q1_v1_20261111_1615.md`.

Section 15 maps every required fix to the change made. Author of the plan: Claude (Anthropic), for Van Thieu. Target journal: Artificial Intelligence in Medicine (AIM) is preferred over IEEE JBHI because of article length.

## 0 Status at writing and what the author had seen

No analysis described here has been run, no data table built, no edge extracted, no method ported, and no proof written. Numbers quoted come only from the P7 HISS manuscript v6 (21/10/2026).

Declarations, so that a reader can judge what the design may have been tuned to:

1. **Concurrent LR and Random Forest results.** When v1 was frozen, LR files already existed for BRFSS 2021 (exhaustive search, 15:19; DiCE random, 16:09) and for NHANES, as did `classifier_robustness_*.csv` (15:54). The author listed file names and modification times only. No file was opened and no coefficient was seen. The primary gradient-method test therefore uses an MLP, for which no output exists.
2. **KDIGO 2024 keyword check.** Before writing v2, the author fetched the open-access PDF (CC BY-NC-ND 4.0), converted it with pdftotext 4.00, and searched it by keyword for indicator-type constructs (Section 4.2).
   - The construct table (Section 4.4) and the section list (Section 4.3) were written after this check. That is a choice made knowing that KDIGO has routes into depression and quality of life, and it favours a non-degenerate graph (review fix 6 and N7e).
   - The extraction prompts will contain no example taken from KDIGO.
   - The extraction agents will not see this plan, the check, or its findings.
3. **WHO HEARTS.** The modules on WHO IRIS returned HTTP 403 to automated requests and were not read. HEARTS-D 2020 (local) was searched by keyword.
4. **P7 results.** The author read P7 v6, including Table 3, Table 7 and §3.2. P7 reports that 99.02–100% of NHIS and NHANES cohort patients can be flipped by one non-indicator change, and that route-aware enforcement and the lock gave the same best counterfactual distance on every NHANES configuration. The expectations in Section 7a are based on these numbers.

## 1 Purpose, headline claim and scope

Headline claim to test (changed in v3):

- The guideline-derived dependency graph, represented as a KG, is an audit and derivation instrument. Applied to a second guideline and disease with a measured outcome (KDIGO 2024 and CKD in NHANES), the role assignment derived mechanically from the graph reproduces the indicator failure. The graph-derived indicator lock then removes it at a small cost, without a hand-made indicator list for the new disease.
- Route-aware enforcement is not claimed to beat the lock. Its equivalence to the lock is tested.

P7 v6 already concluded that recourse systems should recommend levers and treat indicator change as an expected consequence. v3 makes that the tested position.

Extensions:

- **A. Second guideline and disease.** CKD in pooled NHANES, labelled from a single examination, with KDIGO 2024. BRFSS CVD with WHO HEARTS is kept only as an expected-degenerate replication (Section 4.5).
- **B. Further generator–model pairs.** Wachter on an MLP (primary), Wachter on LR, Growing Spheres, Actionable Recourse, and MINT as an illustration only.
- **D. Formalisation.** A precise definition of indicator leakage, with one elementary proposition, lemmas and a corrected causal proposition. The formal part makes the audit precise and is not presented as a contribution in its own right.

Out of scope:

- any human rater (clinician, patient, or the student's own judgement);
- manual annotation by the student;
- longitudinal validation (Section 12).

Relation to earlier manuscripts: the plan assumes a single Q1 article that contains the HISS v6 content plus these extensions, with the FAIR 2026 overlap declared. This is open question 1. Title and abstract will say "a second guideline and disease", not "transfers across diseases", unless the transfer evidence in Sections 4.7–4.8 supports more.

## 2 Definitions inherited from P7 (fixed)

These are from P7 v6 Sections 2.3–2.6 and `<local>` (`nodes.py`, `edges.py`, `audit.py`).

**Roles.** There are four: lever, treatable, indicator, immutable. They are assigned per domain (Section 3). The code has no separate "proxy" role; proxies are immutable.

**BRFSS diabetes role table** (from `nodes.py`; used for H4 and H5, review fix N13):

| Role | Features | Direction |
|---|---|---|
| lever | BMI (bidirectional), PhysActivity, Fruits, Veggies (up), Smoker, HvyAlcoholConsump, NoDocbcCost (down) | as P4 |
| treatable | HighBP, HighChol (down) | as P4 |
| indicator | GenHlth, PhysHlth, MentHlth (down); DiffWalk (conditional, held fixed by the P4 taxonomy, so never movable) | as P4 |
| immutable | Age, Sex, Stroke, HeartDiseaseorAttack, Income, Education, AnyHealthcare, CholCheck | as P4 |

The BRFSS lock set is {GenHlth, PhysHlth, MentHlth}, as in P7. DiffWalk is already immovable.

**Change set and counterfactual categories.**

- Change set S(x, x′): the features that differ after the P4 rounding rule.
- Touches an indicator: S contains an indicator.
- Unsupported (leaks): some indicator in S has no lever in S with a qualifying route (Section 3).
- Fully unactionable: S moves an indicator and contains no lever and no treatable.

**Modes.**

- published: P4 direction constraints only;
- indicator lock: indicators of the domain set immutable;
- route-aware: accept only non-leaking points, with the mechanism depending on the generator (Section 5.3). For DiCE it is P7's rejection and regeneration with seed + 100,000·r for at most 8 rounds.

**Protocol.**

- Split: stratified 80/20, seed 42.
- Cohort: test patients with predicted probability ≥ 0.5, at most the 200 highest-risk.
- No patient below 0.5 is ever included, because a counterfactual is undefined for a patient already predicted negative (review fix N4).
- Generator seeds: 42, 123, 2024, 7, 31337. The model is fitted once per configuration.
- The effective sample is patients. Per-patient means are taken over all returned counterfactuals across seeds.

**Metrics** (defined now):

- **O-share (indicator share of changes):** for each patient, the sum over their counterfactuals of indicator changes divided by the sum of all feature changes (a per-patient ratio of sums). Then the mean over patients.
- **Valid among requested:** valid counterfactuals divided by counterfactuals requested.
  - DiCE: five requested per patient-seed cell.
  - Wachter: one kept output per seed, so five per patient (Section 5.3).
  - Computed per patient, then averaged.
- **Patient coverage:** share of cohort patients with at least one accepted counterfactual.
- **Best counterfactual:** number of changes and normalised L1 distance. Features are scaled to [0, 1] by their P4 permitted range, and the distance is summed over features.
- **Secondary:** distinct counterfactuals per patient; local outlier factor against the training data (scikit-learn defaults, 20 neighbours, scaled features).

**Intervals.**

- Continuous patient means: percentile bootstrap, 2,000 patient resamples, seed 20261111.
- Patient-level proportions (patient coverage, O-A4): Clopper–Pearson exact binomial intervals (review fix N14).
- Numbers in documents are truncated to four decimals (rulebook §5.5).

## 3 The artefact: dependency graph represented as a KG; role derivation

**Starting point.** The export renamed on 11/11/2026: `outputs/kg_export/dependency_graph.ttl`, `dependency_graph_nodes.csv`, `dependency_graph_triples.csv`.

**Node types.**

| Node type | What it is | Identifier |
|---|---|---|
| Concept | clinical or behavioural concept shared across surveys and diseases | public, no-key codes (NCIt, EFO, HPO, MONDO via OLS4; LOINC via NLM Clinical Tables); no SNOMED CT or UMLS |
| Variable | survey or examination item in one dataset | dataset and source variable |
| Domain | a disease model configuration (type 2 diabetes, CKD, CVD) | MONDO code |
| Guideline | one source document | DOI or stable URL |
| Statement | one extracted route, reified | edge identifier |
| RoleAssignment | role and direction of a Concept within a Domain | (concept, domain) |

**Relations.**

- `measures` (from Variable to Concept).
- `assignedIn`, `ofConcept`, `role`, `direction` (on RoleAssignment).
- `recognisedRouteTo` (from Concept to Concept, reified as a Statement). The Statement carries:
  - authority, document, section, page;
  - strength and the guideline's grade;
  - extractor identities and agreement;
  - a paraphrase;
  - a pointer to the quotation record;
  - `population`: the population the statement addresses, for example "people with CKD" (review suggestion S4).
- `scopedTo` (from Statement to Domain).

**Shared nodes.** BMI, physical activity, smoking, blood pressure, cholesterol, self-rated health and depressive symptoms are each one Concept across ADA, KDIGO and HEARTS.

**Role derivation for a new domain** (the transfer step, done by script, not by hand). For each Variable of the new domain:

1. The script follows `measures` to its Concept.
2. If the Concept has a RoleAssignment in the diabetes domain, the role and direction are inherited.
3. A Concept with no earlier assignment gets its role from this fixed rule:
   - a diagnosis-history item, a demographic item or a survey-design variable is immutable;
   - a behaviour the person performs is a lever;
   - a measured clinical risk factor reached through clinical care is treatable;
   - a patient-reported health-status item is an indicator.

   For the CKD domain the new Concepts are Diabetes (immutable, diagnosis history) and Cycle (immutable, design). All other CKD Concepts are shared with diabetes, so their roles are inherited.
4. The generated role table and lock set (all Concepts with role indicator) are written to a file and hashed before any CKD model is fitted.
5. **Role-conflict check.** Any agreed KDIGO Statement that recommends a direct clinical intervention on an inherited indicator Concept is listed, for example pharmacological treatment of depression in Table 38. The primary analysis keeps the inherited role. A sensitivity reading re-labels that Concept as treatable.

**Role grounding without raters.** Indicator Concepts link to:

- the instrument documentation: CDC Healthy Days (HRQOL-4) for GenHlth, PhysHlth and MentHlth; PHQ-9 for the NHANES MentHlth proxy;
- LOINC codes, looked up by script.

This is documentation of what the items are, not a rating.

**Route-aware enforcement as a path constraint.** For change set S, domain d, authority set 𝒜, strength set 𝒮 and path bound k:

> accept(S) holds if and only if, for every v in S with role(v, d) = indicator, there is a u in S with role(u, d) = lever and a directed path from u to v of at most k `recognisedRouteTo` steps. Every Statement on the path must have authority in 𝒜 and strength in 𝒮, and every intermediate node must have role treatable in d.

Readings:

- **Primary:** k = 1, 𝒜 = primary authority of the domain (Section 4.3), 𝒮 = all.
- **Secondary:**
  - k = 2 with the intermediate not required to be in S (the permissive reading fixed in v2);
  - k = 2 with the intermediate required to be in S (strict; review suggestion S6);
  - 𝒜 = union of authorities;
  - 𝒜 = authorities of the other domain;
  - 𝒮 = graded only;
  - in-scope: an edge applies only to cohort patients inside its `population`, for example patients with the CKD label.

**Software check.** The Python implementation (`depgraph.audit.classify` with domain tables) and a SPARQL ASK query over the Turtle export (rdflib) must agree on 100% of audited counterfactuals. A disagreement is a bug (Section 9).

**Claims.** Edges are guideline-derived, not causal, and carry no effect size. A supported route does not bound the size of the indicator change it licenses. Route-aware enforcement accepts MentHlth moving from 30 to 0 days on the strength of "exercise for depression". For this reason the headline uses the lock, and change sizes are reported (Section 4.7).

## 4 Extension A: second guideline and disease

### 4.1 Questions

- **A-Q1 (transfer, confirmatory).** With roles derived mechanically from the graph, do generators place changes on indicators in the CKD domain beyond what movability explains, and leave counterfactuals with nothing to act on?
- **A-Q2 (confirmatory).** Does the graph-derived indicator lock remove this at a small cost?
- **A-Q3 (confirmatory, equivalence).** Is route-aware enforcement with KDIGO routes equivalent to the lock?
- **A-Q4 (key secondary).** Do routes carry across guidelines? That is, do ADA-only and KDIGO-only audits agree on CKD counterfactuals?

### 4.2 Pre-plan route check (unchanged from v2)

KDIGO 2024 states lever-to-indicator routes:

- Table 38 (§5.2.3, p. S259, lifestyle column) lists:
  - exercise for depression, pain and sleep disorders;
  - physical activity for poor appetite.
- Figure 17 (§3.1) gives the narrative goal of maximising health-related quality of life and physical function.
- Practice Point 5.2.3.1 states the aim of improving health-related quality of life.

Keyword counts: "quality of life" 20, "depress" 17, "fatigue" 8, "physical function" 3.

WHO HEARTS: the modules were not readable. HEARTS-D 2020 contains no route into an indicator-type construct and is ungraded.

### 4.3 Authority sets, sections, licence and grading

**Authority sets** (fixed by student decision, 11/11/2026):

| Domain | Primary 𝒜 | Document | Sections (exhaustive) |
|---|---|---|---|
| CKD (primary) | {KDIGO 2024} | [10.1016/j.kint.2023.10.018](https://doi.org/10.1016/j.kint.2023.10.018) | §3.1 (with Figure 17), §3.2, §3.3, §3.4, §3.5, §3.15; §5.2 (with Tables 37 and 38) |
| CVD (expected-degenerate replication) | {WHO HEARTS} | modules WHO/NMH/NVI/18.1, 18.2, Risk-based CVD management (2020) | all sections of the three modules |
| Diabetes (P7) | {ADA 2026} | unchanged | unchanged |

Sections not listed are not extracted. A cross-reference counts only if the referring sentence states the route.

**Licence: (a) automated extraction.**

- KDIGO 2024: CC BY-NC-ND 4.0.
- HEARTS: CC BY-NC-SA 3.0 IGO.

Both permit copying and processing for non-commercial purposes. No statutory text-and-data-mining exception is relied on.

**Licence: (b) sending text to Claude.** This was decided in v3 and is no longer a gate.

- The NC clause restricts the purpose of use: the use may not be primarily intended for commercial advantage or monetary compensation.
- Here the purpose is non-commercial academic research by a student at a public university, with no commercial product, advantage or compensation sought.
- Sending the text to an API service that processes it on the licensee's behalf, for that purpose, is part of the licensee's own use. It is not a public sharing of the work.
- The text is sent with its attribution and licence notice.
- The ND and SA terms govern distribution of adaptations, and are handled by the release rule below.

**Released KG licence: CC BY-NC-SA 4.0.** Verbatim text is handled per source (review suggestion S8):

- **ADA and KDIGO:** the release contains no verbatim text (locator, strength, grade and paraphrase only). Quotations stay in a local audit file that is not released. The current export already carries no ADA quotation.
- **HEARTS and HEARTS-D:** quotations may be released, because their NC-SA terms are compatible with the release licence.
- **Vietnamese MoH Decision 5481:** quotations may be released, because official legal documents are not protected works under Article 15 of the Vietnamese Law on Intellectual Property.

The existing export already ships five MoH quotations and one HEARTS-D quotation, consistent with this rule.

**Grading for the secondary evidence-support scores.**

- **KDIGO:** 1A 0.9; 1B 0.7; 1C or 1D 0.5; any grade 2 0.3; practice point, table entry or explicit ungraded statement 0.6; narrative 0.2.
- **HEARTS:** ungraded, so explicit ungraded 0.6 or narrative 0.2.
- **ADA:** as P7.

### 4.4 Edge extraction protocol

**Candidate pairs.** All ordered pairs (u, v) of domain concepts with u ≠ v, role(u) in {lever, treatable} and role(v) in {lever, treatable, indicator}. An edge is recorded only when the text states that acting on the source changes the target. Each edge records source, target, strength, grade, page, section, a quotation of at most twelve words, a paraphrase and the population addressed.

**Construct mapping, targets.** Fixed now. It was written after the KDIGO keyword check (Section 0, item 2).

| Guideline construct | NHANES item | BRFSS item |
|---|---|---|
| overall or general health, health-related quality of life, quality of life, general well-being | GenHlth (`HUQ010`) | GenHlth |
| depression, depressive symptoms, low mood, anxiety, psychological or emotional distress, mental health | MentHlth (PHQ-9 proxy) | MentHlth |
| physical function, functional capacity, daily activity, mobility, pain, fatigue, physical symptoms | none | PhysHlth; DiffWalk only for mobility or walking |
| sleep, appetite, nausea, pruritus | none | none |
| weight, body mass index, obesity | BMI | BMI |
| blood pressure, hypertension | HighBP (measured, Section 4.5) | HighBP |
| cholesterol, lipids, dyslipidaemia | HighChol (measured, Section 4.5) | HighChol |

**Construct mapping, sources** (review fix N8):

| Guideline construct | NHANES item | BRFSS item |
|---|---|---|
| exercise, physical activity, sedentary behaviour (reduce) | PhysActivity: 2017–2020 `PAQ605` (vigorous work activity); 2021–2023 leisure-time minutes (`PAD790`–`PAD820`) | PhysActivity (`_TOTINDA`) |
| smoking, tobacco use, cessation | Smoker (current) | Smoker |
| diet, nutrition, weight loss, energy deficit | BMI (weight loss); diet items have no NHANES feature | BMI; Fruits, Veggies for fruit and vegetable intake |
| alcohol | none in the CKD feature set | HvyAlcoholConsump |

**Threat stated now.** Mapping "exercise" onto occupational vigorous activity (`PAQ605`) in 2017–2020 is a construct mismatch. The 2021–2023-only analysis, where the item is leisure-time activity, is the better-matched sensitivity analysis for routes from exercise.

**Extractors.**

- **Extractor 1:** Claude through the Anthropic API.
- **Extractor 2:** Qwen2.5-7B-Instruct, GGUF Q4_K_M, run locally on CPU with llama.cpp build b12283 (`<local>`). The model is in `<local>`. Approved by the student.
- Extractors run in separate sessions, without access to each other's output, to this plan, or to the pre-plan check.

**Chunking, identical for both extractors** (review fix N7c):

- Unit: one listed section, or one table, per call.
- A unit longer than 6,000 tokens is split into consecutive chunks of at most 6,000 tokens with a 500-token overlap.
- Context: 16,384 tokens for the local model. Maximum output: 2,048 tokens. Temperature 0 for both extractors.
- The same chunk files are given to both extractors.

**Recall gate for the local model** (review fix N7d; fixed now, run before KDIGO extraction):

- The local model runs the frozen prompt on P7's sources with agreed Claude extractions, `killtest_x5/sources/`:
  - WHO HEARTS-D 2020: one agreed edge;
  - Vietnamese MoH 5481/QĐ-BYT: five agreed edges;
  - NICE NG28: no agreed edge.
- The gate passes if it recovers the HEARTS-D edge and at least 3 of the 5 MoH edges.
- NG28 output is reported as a false-positive count.
- If the gate fails, the fallback decided in v2 is used: a second Claude instance with an independently written second prompt. The paper then states that the extractors share a model family.

**Frozen and hashed before extraction.** Prompts, model identifiers and settings, chunk files, PDFs, both text conversions (`pdftotext -layout` and `pdftotext -raw`), the section list and the construct tables. Their SHA-256 values are added to the manifest.

**Quotation check** (review fix N7a, N7b). Fixed now:

1. Quotation tokens are lower-cased and stripped of punctuation.
2. A quotation passes if its tokens occur contiguously in the `-raw` text of the cited page, or in order within a window of three consecutive lines of the `-layout` text of that page. The second rule covers table cells split across columns.
3. A failing quotation drops the edge only from the set of the extractor that produced it.
4. Drop counts are reported per extractor.

**Agreement and graph.**

- Agreement: Cohen's κ, positive and negative agreement, and PABAK over the candidate pairs.
- The graph is the intersection: edges both extractors found, each with a verified quotation. The union is a secondary reading. No person adjudicates.

### 4.5 Data and variables

**Primary: CKD, NHANES 2017–2020 (`P_` files) and 2021–2023 (`_L` files), pooled.**

Analytic sample (review fix N12), in this order, with a flow diagram of counts:

1. Participants aged 20 years or older (P7 convention).
2. Examined at the mobile examination centre (`RIDSTATR` = 2).
3. Not pregnant (`RIDEXPRG` ≠ 1).
4. Label rule:
   - positive if either available test is positive: eGFR < 60 mL/min/1.73 m², from `LBXSCR` (`P_BIOPRO`/`BIOPRO_L`) with the CKD-EPI 2021 creatinine equation, age and sex; or urine albumin-to-creatinine ratio `URDACT` ≥ 30 mg/g (`P_ALB_CR`/`ALB_CR_L`);
   - negative only if both tests are available and both are negative;
   - missing otherwise, and excluded.
5. Complete cases on all features (as P7).

What the label is: reduced eGFR or albuminuria at a single examination. It has no three-month persistence, so it is not a clinical CKD diagnosis. The model detects current state and is not a risk model, as P7 v6 already says for diabetes. A class flip is not lower risk of kidney failure. eGFR < 60 is largely irreversible, and CKD-EPI includes age, so the high-risk cohort is expected to be older. Both points are stated as threats.

**CKD features.**

| Feature | Source | Role (derived, Section 3) | Direction |
|---|---|---|---|
| Diabetes | `DIQ010` = 1 (borderline as sensitivity coding) | immutable (new concept, rule) | immutable |
| HighBP | measured: mean of available `BPXOSY1`–`BPXOSY3` ≥ 130 mmHg (`P_BPXO`/`BPXO_L`) | treatable (inherited) | down |
| HighChol | measured: `LBXTC` ≥ 240 mg/dL (`P_TCHOL`/`TCHOL_L`) | treatable (inherited) | down |
| BMI | `BMXBMI`, integer | lever (inherited) | bidirectional |
| Smoker (current) | `SMQ020` = 1 and `SMQ040` in {1, 2} | lever (inherited) | down (cessation) |
| PhysActivity | as P7 per cycle | lever (inherited) | up |
| GenHlth | `HUQ010` | indicator (inherited) | down |
| MentHlth | PHQ-9 total in P7 bands | indicator (inherited) | down |
| Stroke; HeartDiseaseorAttack | `MCQ160F`; `MCQ160C` or `MCQ160E` | immutable (inherited) | immutable |
| Age, Sex, Education, Income, AnyHealthcare | as P7 | immutable (inherited) | as P4 |
| Cycle | 0 = 2017–2020, 1 = 2021–2023 | immutable (new concept, rule) | immutable |

Notes on the feature set:

- **Measured state** (review fix N9). HighBP and HighChol are measured states, not "ever told" items, so a decrease means control, not un-diagnosis. Sensitivity: ever-told `BPQ020` and `BPQ080` as immutable instead.
- **Smoking.** Current smoking replaces `SMOKE100` in the CKD domain.
- **Survey weights.** Not used. The estimands are conditional on the analytic sample, the fitted model and the cohort, and no population inference is made. NHANES oversamples older, minority and low-income adults, so the cohort is not representative. Sensitivity (review suggestion S2): XGBoost refitted with the examination weights (`WTMECPRP` for 2017–2020, `WTMEC2YR` for 2021–2023, names checked at A0) as `sample_weight`; O-A1 and O-share reported.
- **Pooling.** Cycle is an immutable feature. Sensitivity analyses on 2017–2020 alone and 2021–2023 alone. O-A1 and O-share are also reported per cycle (review suggestion S3).
- **Less-exposed cohort.** Participants with self-reported kidney disease (`KIQ022` = 1) are excluded and H1–H3 outcomes re-estimated.
- **Pre-generator model property** (review suggestion S1). After the model is fitted and before any generator runs, the share of cohort patients who can be flipped by a single non-indicator change is computed. It is reported whatever the results.

**Expected-degenerate replication: CVD, BRFSS 2021** (review suggestion S5).

- Label `_MICHD`. Roles derived by the transfer step.
- Diabetes `DIABETE4` = 1 only. Current smoking `_RFSMOK3` (name verified at A0). `NoDocbcCost` kept as the P4 lever.
- Gates before any run: `TOLDHI3` coverage, with HighChol dropped if partial; the HEARTS PDFs obtained manually.
- Threats: reverse causation (`_MICHD` is a past event), and an expected degenerate graph.
- It is reported only descriptively, and as not reached if the gates fail.

**Removed.** The Pooled Cohort Equations negative control is removed (review fix N11). Its feature set could not make the label a function of the features without adding inputs outside the domain. A control that does not separate generator from label adds nothing.

### 4.6 Models, generators and cohort

**Models.**

- Primary: XGBoost with the P4 configuration, threads unchanged.
- Secondary: LR and Random Forest with the configuration of `p7_cross_classifiers.py`.

**Generators.**

- DiCE random for H1 and H2.
- The exhaustive sparse search for H3 and for the secondary lock costs.
- DiCE genetic: secondary.

**Cohort** (review fix N4). Test patients with predicted probability ≥ 0.5, at most 200. If fewer than 50 qualify, the CKD primary tests are reported as not reached. Otherwise they run on the patients who qualify, with n reported. Thresholds are never mixed.

### 4.7 Outcomes

**Primary, CKD (pooled NHANES, XGBoost, derived roles).**

- **O-A1:** fully unactionable share, published mode, DiCE random.
- **O-A2 (per-patient movability null; review fix N1).**
  - For patient i, let M_i be the features movable for that patient: A*_f(x_f) contains a value other than x_f. Let n_i be the number of indicators in M_i.
  - Under the null, the indicator labels fall on a uniformly random subset of size n_i of M_i, independently across patients.
  - The statistic T is the mean over patients of the observed O-share. The null distribution of each patient's O-share is enumerated exactly over all subsets (at most 45 in CKD, counting Education, Income and AnyHealthcare as movable upward under the P4 direction rules; at most 1,001 on BRFSS). The distribution of T is obtained from 100,000 Monte Carlo draws of one subset per patient (seed 20261111).
  - p = (1 + number of draws with T* ≥ T) / 100,001. Patients with n_i = 0 contribute 0 to both T and T*.
  - Residual limitation: a multi-level feature can move by small amounts more easily than a binary one, so movability does not remove all differences in ease of change.
- **O-A3:** change in valid among requested, lock minus published, DiCE random, with patient coverage under the lock.
- **O-A5:** per-patient difference in normalised L1 distance of the best counterfactual, lock minus route-aware, exhaustive search. It can be negative: Lemma 3 orders counterfactuals lexicographically (number of changes first, then distance), so a route-aware counterfactual with fewer changes may have a larger distance. A patient with no lock counterfactual follows the P7 pairing rule.

**Key secondary.**

- **O-A4:** share of patients whose best route-aware counterfactual is strictly better than the best lock counterfactual (fewer changes, or equal changes and smaller distance), with a Clopper–Pearson interval.
- **Change sizes** (review fix N3): among route-supported counterfactuals that move an indicator, the distribution of the change size, in GenHlth levels and in PHQ-9 bands, per supporting lever.
- **Capped reading:** route-aware acceptance with a supported indicator allowed to move at most one GenHlth level or one PHQ-9 band per supporting lever.
- Leakage under all readings; touch share.
- Route-aware cost against published (DiCE random), with coverage.
- Exhaustive-search costs (changes, distance, coverage) under lock and route-aware.
- **Cross-guideline agreement** (A-Q4; review fix N2):
  - Population: indicator-touching CKD counterfactuals, published mode, all generators.
  - Comparison: verdicts (supported or unsupported) under 𝒜 = {ADA} and under 𝒜 = {KDIGO}.
  - Statistics: raw agreement and Cohen's κ, with 95% intervals.
  - Reading rule, fixed now: raw agreement ≥ 0.80 reads as "routes carry across the two guidelines"; < 0.60 reads as "guideline-specific"; values in between are reported as partial.
  - The reverse comparison is also reported: P7 diabetes counterfactuals with KDIGO routes added.

**Other secondary.**

- DiCE genetic; LR and Random Forest; the less-exposed cohort; per-cycle and single-cycle analyses; the weighted refit; ever-told sensitivity; the role-conflict sensitivity; the in-scope reading.
- Edge-permutation null: edges into indicators permuted among indicators, keeping their number, 1,000 permutations.
- κ and PABAK; evidence-support scores; local outlier factor; distinct counterfactuals; the BRFSS CVD replication.

### 4.8 Decision criteria for A (fixed now)

There are five primary hypotheses (H1–H5), with Bonferroni family-wise α = 0.05, so α = 0.01 each (Section 8).

**H1 (transfer: the derived roles reproduce the failure).** Supported only if both components hold:

- (i) Replication check: the lower 99% bootstrap bound of O-A1 exceeds 0.10. This component is expected to pass. P7 v6 Table 3 reports 19.07–22.85% fully unactionable on NHANES diabetes with a similar feature schema. It is therefore a replication check, not a confirmatory finding.
- (ii) Confirmatory component: the per-patient movability null of O-A2 gives p < 0.01. This component carries the information, namely that generators place changes on indicators beyond what each patient's movable set explains.

Not supported if the upper bound of O-A1 is at most 0.10, or p ≥ 0.5. Undecided otherwise.

**H2 (the graph-derived lock is cheap).** Supported if both hold:

- the lower 99% bootstrap bound of O-A3 exceeds −0.05;
- lock patient coverage, as a point estimate, is at least 0.95.

Not supported if the upper bound is below −0.05 or coverage is below 0.95. Undecided otherwise.

Margin: 0.05 absolute is a convention, the stricter end of the 5–10-point absolute non-inferiority margins commonly used for proportions. It is not derived from P7, and it is stated as a convention. The realised relative loss is reported.

**H3 (route-aware enforcement is equivalent to the lock).** Tested with two one-sided tests (TOST) at α = 0.01, that is, a 98% percentile bootstrap interval for the mean of O-A5, against the margin δ = 0.05 in normalised L1 distance.

- **Justification of δ, domain-free.** 0.05 is less than one grid step of every ordinal or binary feature except day counts in both domains: GenHlth one step = 0.25, binary features = 1. It equals 1.5 days of MentHlth on a 0–30 grid, or about 0.8 BMI units on the P4 range 18.5–35. A mean difference below δ means the lock costs less than one step of a typical feature.
- **Verdicts.**
  - Supported (equivalent): the 98% interval lies inside (−0.05, 0.05).
  - Not supported (not equivalent): the lower bound is at least 0.05 (route-aware closer by a non-negligible amount) or the upper bound is at most −0.05 (lock closer by a non-negligible amount).
  - Undecided otherwise.
- **Expected result:** supported, given P7 v6 Table 7 and the 99.02–100% single non-indicator flip rate. This is stated in advance, and a pass is read as "routes add nothing over the lock in recourse generation". That reading is consistent with the headline that the graph's value is audit and derivation.

**Degenerate and near-degenerate graphs** (review fixes 5 and N2).

- **Degenerate:** the KDIGO intersection graph has no edge into GenHlth or MentHlth.
  - Route-aware equals the lock, and H3 is reported as "not testable: degenerate graph".
  - A-Q4 is reported, and the paper describes CKD as a domain where the guideline gives no agreed route into the survey indicators.
- **Near-degenerate:** edges into an indicator exist, but every supporting lever is movable for fewer than 10% of cohort patients. H3 is then reported with this flag, and its equivalence is not counted as evidence about the graph.

**Overall reading of A.**

- H1 and H2 supported: roles derived from the graph carry the failure to a second guideline and disease with a measured outcome, and the derived lock removes it cheaply.
- H3 supported: route enforcement adds nothing over the lock there.
- A-Q4 states whether routes carry across guidelines.
- H1 not supported: the failure was not shown beyond movability in this domain, and the claim narrows to the P7 diabetes data.

Every verdict is reported.

## 5 Extension B: further generator–model pairs

### 5.1 Methods (closed list)

| Method | Family | Reference | Models | Status |
|---|---|---|---|---|
| Wachter | gradient-based | [10.2139/ssrn.3063289](https://doi.org/10.2139/ssrn.3063289) | MLP (primary), LR (secondary) | primary (H4, H5) |
| Growing Spheres | model-agnostic sampling | [arXiv:1712.08443](https://arxiv.org/abs/1712.08443) | XGBoost | secondary |
| Actionable Recourse | integer programming | [10.1145/3287560.3287566](https://doi.org/10.1145/3287560.3287566) | LR | secondary |
| MINT | causal recourse | [10.1145/3442188.3445899](https://doi.org/10.1145/3442188.3445899) | XGBoost | illustration of Proposition 2 only |

FACE is removed. No method will be added. CARLA: [arXiv:2108.00783](https://arxiv.org/abs/2108.00783), MIT licence.

### 5.2 Environment and Wachter parity

**Environment.** A Python 3.12 virtual environment at `<local>` (approved), with the P4 pins plus CPU torch and python-mip. A Python 3.7 environment is not approved.

**Vendored code.** CARLA method code is vendored from a pinned commit into `tools/q1_generators/vendor/`, with the commit hash and per-file SHA-256 recorded.

**Model identity.** Models must match the P4 venv bit for bit (test AUC and cohort identifiers). Otherwise the saved XGBoost JSON is loaded.

**Wachter parity, cheapest route first.**

1. **Byte-identical core function, with one required edit** (review fix N6). CARLA's Wachter loop (`carla/recourse_methods/catalog/wachter/library/wachter.py`) has a wall-clock stopping rule, `t_max_min`. That rule would make results depend on machine load. It is therefore disabled: `t_max_min` is set so it can never bind, and stopping uses only the iteration cap (1,000 iterations per λ step, as in the vendored defaults).
   - The λ update rule of the vendored code is kept and documented in the run log.
   - Because this edit is required, parity follows route 2.
2. **Reference tests.**
   - The unedited CARLA function, run under torch 2.x on a synthetic dataset generated in our code, with `t_max_min` set large enough not to bind.
   - The edited function must give the same counterfactuals within 10⁻⁴ per coordinate on that dataset.
   - CARLA's own Wachter test configuration provides the settings.
3. **Python 3.7 fallback.** Only if the unedited function cannot run under torch 2.x is a Python 3.7 environment needed. This is flagged to the student before anything else in B runs.

### 5.3 How the dependency graph enters each method

**Scaling and rounding.**

- Features are scaled to [0, 1] by their P4 range.
- L1 distance (Wachter, Actionable Recourse, the exhaustive search) and L2 distance (Growing Spheres) are computed in the scaled space.
- Rounding to the P4 grid happens once, at the end.
- Filtering and nearest-point selection are done on rounded points.
- Validity is reported before and after rounding.

**Wachter, equal search effort in every mode** (review fix N5). Let P be the number of route patterns in the configuration (P = 24 on BRFSS diabetes with the ADA graph). In every mode, for each of the five seeds, Wachter is run P times and the valid rounded result of lowest scaled L1 cost is kept, so one kept output per seed.

- **Published and lock:** P random starts x + N(0, 0.01²), sub-seeds seed·1,000 + j, j = 1…P.
- **Route-aware:** one run per pattern, each from a random start with the same sub-seeds.
  - In a pattern, each indicator v is either locked, or free with one ADA lever parent forced to move at least one grid step in its permitted direction.
  - On BRFSS diabetes the 24 patterns are:
    - GenHlth: locked, or BMI forced, or PhysActivity forced;
    - PhysHlth: locked, or BMI, PhysActivity or Smoker forced;
    - MentHlth: locked, or PhysActivity forced.
    - DiffWalk is immovable.
  - The rounded result must pass the path constraint.

Valid among requested for Wachter is the number of valid kept outputs divided by 5 per patient.

**Other methods.**

| Method | Published | Lock | Route-aware |
|---|---|---|---|
| Growing Spheres | immutables and directions enforced by rejection; CARLA defaults (1,000 samples per layer, step 0.2) in scaled space; five seeds | indicators fixed | rounded candidates violating the path constraint removed before the nearest valid one is chosen |
| Actionable Recourse | action set from direction and range; flipset of size 5 | indicator actions removed | z_v ≤ Σ z_u over lever parents u of v, as an integer-programming constraint |

**MINT** (unchanged from v2).

- Linear additive-noise SCM on the primary-authority graph, fitted by OLS on the training split.
- Abduction, then topological rounding (A7).
- Interventions on at most three levers, chosen by brute force at minimum L1 action cost.
- The audited change set is the interventions plus the propagated changes, reported separately.
- No lock row. MINT is used only as a numerical check of Proposition 2.

### 5.4 Order, freezing and budgets

1. All ports and all unit tests (Section 5.6) pass, and all scripts are hashed into the manifest, before any real-data run.
2. Runs follow the order Wachter, Growing Spheres, Actionable Recourse, MINT.
3. Budgets per method × model × configuration × mode: 4 CPU-hours of process CPU time (psutil), and 2 × 10⁷ model evaluations for brute-force searches. Exceeding a budget means "not reached".
4. No replacement method is chosen after any result. If Wachter on the MLP is not reached, H4 and H5 are not tested.

### 5.5 Data, outcomes and decision criteria for B

**Primary configuration.** BRFSS 2021 diabetes, with the P7 loader and the role table of Section 2.

**MLP.** Hidden layers 18, 9, 3, ReLU; Adam, learning rate 0.002, batch 1,024, 20 epochs, seed 42; scaled features. The cohort follows the P7 rule (no patient below 0.5).

**Secondary configurations.** The other P7 diabetes configurations and the CKD primary configuration.

**LR port check** (secondary). The expected first moved feature is predicted from the coefficients and scaled costs, and its agreement with the actual output is reported as a check of the port.

**H4 (generator–model pair Wachter on MLP places changes on indicators beyond movability and leaves non-actionable counterfactuals).** Published mode. Supported if both hold:

- the lower 99% bound of the fully unactionable share exceeds 0.10;
- the per-patient movability null of Section 4.7 gives p < 0.01. On BRFSS, M_i includes up to three movable indicators.

Not supported and undecided as for H1. No P7 result exists for this pair, so neither component is predictable from P7.

**H5 (the lock is cheap for this pair, under equal search effort).** Lock minus published, both with P restarts. Supported if both hold:

- the lower 99% bound of the change in valid among requested exceeds −0.05;
- lock patient coverage is at least 0.95.

Not supported and undecided as for H2.

**Secondary.**

- Route-aware against lock: equivalence of the best kept cost, with the same TOST and δ as H3.
- Leakage under all readings; change sizes.
- Validity before and after rounding; distance; changes; local outlier factor; distinct outputs; CPU time.

**Reading.** Results are read for the generator–model pair, not for the generator alone (review 2.5). A failed H4 means "not shown for this pair". It does not mean "leakage is generator-dependent".

### 5.6 Unit tests (must pass before any real-data run)

- **Wachter, L2:** matches the closed-form boundary projection on a synthetic linear model, within 10⁻³ (20 points).
- **Wachter, L1:** changes only the feature with the largest |w_j|/cost_j ratio, within 10⁻³.
- **Wachter, mask and projection:** immutables never change; directions and ranges hold at every iteration; forced pattern moves survive rounding.
- **Wachter, no wall-clock dependence:** two runs with an artificial CPU load give identical outputs.
- **Growing Spheres:** valid, within one step of the boundary, mask respected (two-feature linear problem).
- **Actionable Recourse:** flipset equals the enumerated optimum; indicator-only actions excluded under the route constraint.
- **MINT:** abduction-action-prediction matches the closed form on edges (a, b), (b, c); a parent change that rounds to zero leaves the child unchanged.
- **Route constraint (all methods):** a synthetic patient whose only cheap flip is indicator-only leaks in published mode, and is supported or empty in route-aware mode.
- **Path constraint:** Python and SPARQL agree on 10,000 random change sets.
- **Movability null:** on a toy cohort, the exact per-patient enumeration matches brute force, and p is uniform under a generator that changes movable features uniformly at random (1,000 simulated cohorts; Kolmogorov–Smirnov p > 0.01).

### 5.7 Compute

- CPU only, this Windows machine, below-normal priority, at most two heavy processes.
- BLAS and OpenMP limited to 2 threads, except XGBoost, which keeps the P4 configuration.
- Seeds:
  - generators: 42, 123, 2024, 7, 31337;
  - DiCE regeneration: seed + 100,000·r;
  - Wachter restarts: seed·1,000 + j;
  - bootstrap, permutation and Monte Carlo: 20261111.
- Overnight runs keep a 2–3 hour machine rest.
- Each run writes a log and a JSON of its configuration.

## 6 Extension D: formalisation

### 6.1 Definitions

**Setting.**

- Domain d, feature set F, and role map ρ_d from F to {L, T, I, M}.
- Reference system: the P4 product set C*(x) = ∏_f A*_f(x_f).
- A per-feature system is a product C(x) = ∏_f A_f(x_f) with A_f ⊆ A*_f.
- The classifier has h(x) = 1, and x′ is valid if h(x′) = 0.
- S(x, x′) is the change set after rounding ψ.

**Graph.** G = (F, E), with sources in L ∪ T and targets in L ∪ T ∪ I. So no edge leaves an indicator, and no edge touches an immutable.

**Reachability.** reach_k(u, v) holds if there is a path of at most k edges from u to v whose edges satisfy 𝒜 and 𝒮 and whose intermediate nodes are in T. Intermediate nodes need not be in S.

**Definition 1 (route support).** An indicator v in S is supported if some u in S with ρ_d(u) = L satisfies reach_k(u, v).

**Definition 2 (leakage).** x′ leaks if S contains an unsupported indicator. Pure leakage means x′ leaks and S has no lever and no treatable.

**Definition 3.** R_G(x) is the set of non-leaking points. Route-aware enforcement accepts exactly R_G(x) ∩ C*(x).

### 6.2 Proposition 1 (corrected; review fix N10)

**Assumption A0 (status quo allowed):** x_f ∈ A_f for all f.

**Proposition 1.** Let v be an indicator movable in C*(x). Under A0:

- (i) every per-feature system C ⊆ C* with no leaking point locks v;
- (ii) if some lever u with an edge (u, v) satisfying 𝒜 and 𝒮 is movable in C*, every such C excludes the point that changes exactly u and v, which lies in R_G(x) ∩ C*.

Hence no per-feature system satisfying A0 has R_G(x) ∩ C* as its feasible set when such u and v exist. Under A0, the per-feature systems with no leaking point are exactly those that lock every movable indicator.

**Proof sketch.**

- (i) If A_v contains v′ ≠ x_v, then by A0 the point that changes only v lies in C, and it leaks.
- (ii) If C locks v, the point that changes u and v is excluded. That point is in C*, because u and v are movable and every other feature keeps x_f by A0. It is in R_G, because u is in S and reach_1(u, v) holds.

**Without A0 the statement fails.** A system that forces u to change (A_u = {u′}) can admit v-changes without leakage. The machine check therefore also enumerates systems without A0.

This result is elementary. Mahajan, Tan and Sharma (2019) and Karimi et al. (2021) make the general point about unary versus cross-feature constraints. The paper claims only the form for roles and guideline routes.

**Remark 1.** A generator that returns the lexicographic minimum over valid points of C* returns a leaking point whenever that minimum is an indicator-only change.

### 6.3 Lemmas and Proposition 2 (corrected)

**Assumptions.**

- A1: same ψ and change rule in audit and enforcement.
- A2: same G, ρ_d, k, 𝒜 and 𝒮.
- A3: fixed role partition per domain.
- A4: finite grid and deterministic h.
- A5: independent regeneration rounds.
- A6: interventions on Π ⊆ L in an SCM whose graph is a subgraph of the audit graph restricted to 𝒜 and 𝒮; indicators never intervened; noise fixed by abduction.
- A7: topological rounding. Each node is computed from rounded parent values and then rounded. A non-intervened node with unchanged parents is unchanged.

**Lemma 1 (soundness).** Under A1–A3, no accepted counterfactual leaks.

**Lemma 2 (maximality).** The accepted set is exactly R_G(x) ∩ C*(x). Under the conditions of Proposition 1 (ii), it strictly contains the lock's feasible set.

**Lemma 3 (exhaustive search).** Under A4:

- the filtered search returns a counterfactual if and only if a valid point of R_G ∩ C* exists within its sparsity bound and grid;
- its best route-aware counterfactual is never worse, in the lexicographic order, than its best lock counterfactual.

The ordering is lexicographic only; O-A5 compares distance alone and can be negative.

**Lemma 4 (bound).** Under A5, a cell stays empty after R rounds with probability at most (1 − p)^R. This is a bound only and is not compared with data.

**Proposition 2 (corrected; review fix N10).** Assume A1–A3, A6 and A7. Let t be the largest number of treatable nodes on any directed path of G. Then:

- every changed indicator v has a lever u in S with a path from u to v whose intermediate nodes are treatable and number at most t;
- hence no counterfactual leaks under the path reading with k ≥ 1 + t;
- under k = 1, v leaks if and only if no lever in S has a direct edge into v.

**Proof sketch.**

1. By A7, a changed non-intervened node has a changed parent.
2. Indicators are not intervened and have no outgoing edges. So following changed parents back from v gives a chain of changed nodes that ends at an intervened lever.
3. Take the lever on the chain closest to v. It is in S. The nodes after it are not levers, by the choice of the closest lever; not indicators, because indicators have no outgoing edges; and not immutables, because immutables have no edges. So they are treatable.
4. That segment is a path with at most t treatable nodes, hence at most t + 1 edges.
5. The k = 1 statement follows from Definition 1.

### 6.4 Proved, machine-checked, illustrated

**Proved** (supplementary appendix): Proposition 1, Remark 1, Lemmas 1–4 and Proposition 2.

**Machine-checked** (brute force; not a rating). On the ADA graph and the KDIGO intersection graph, each feature is reduced to at most three grid values and change sets to at most three changes. The script enumerates all points and checks:

- Proposition 1 (i) and (ii), over all product subsystems, including systems without A0, to confirm that A0 is needed;
- Lemma 2;
- Lemma 3, for 100 random threshold classifiers;
- Proposition 2, for 100 random linear SCMs on the graph with A7, at k = 1 + t and at k = 1.

**Checked by a fresh agent:** the written proofs.

**Illustrated:** the leakage rates of real generators.

**Not claimed:** causal validity, effect sizes or clinical usefulness.

**D succeeds** if every statement passes both checks, possibly after correction. A failing statement is downgraded to a conjecture or dropped, and the paper says so.

## 7 Hypotheses at a glance

| ID | Ext. | Statement | Decision rule |
|---|---|---|---|
| H1 | A | derived roles reproduce the failure in CKD (pooled NHANES, XGBoost, DiCE random) | (i) replication check: lower 99% bound of fully unactionable > 0.10; and (ii) confirmatory: per-patient movability null p < 0.01 |
| H2 | A | the derived lock is cheap (DiCE random) | lower 99% bound of Δ valid among requested (lock − published) > −0.05 and lock coverage ≥ 0.95 |
| H3 | A | route-aware is equivalent to the lock (exhaustive search) | TOST α = 0.01, δ = 0.05: 98% interval of mean O-A5 inside (−0.05, 0.05); "not testable" if degenerate; flagged if near-degenerate |
| H4 | B | Wachter on MLP, BRFSS diabetes, beyond movability | as H1 |
| H5 | B | lock cheap for Wachter on MLP under equal restarts | as H2 |
| S-A, S-B | A, B | all analyses listed as secondary in Sections 4.7 and 5.5 | 95% intervals (Clopper–Pearson for patient proportions), descriptive |
| P1, P2, L1–L4 | D | Section 6 | proof plus machine check plus fresh-agent check |

### 7a Expected results, stated before running (review suggestion S7)

| Hypothesis | Expected | Basis |
|---|---|---|
| H1 (i) | pass | P7 v6 Table 3: 19.07–22.85% fully unactionable on NHANES diabetes |
| H1 (ii) | uncertain | no earlier test conditioned on movability |
| H2 | likely pass for the lock; DiCE random coverage is 1 by design | P7 v6 §2.6, Table 3 |
| H3 | likely supported (equivalent) | P7 v6 Table 7 and §3.2 |
| H4, H5 | uncertain | no earlier result for this pair |
| A-Q4 | uncertain | KDIGO routes into MentHlth may exist where ADA has PhysActivity to MentHlth (narrative) |

## 8 Statistics and multiplicity

**Family.** The five primary hypotheses form one family. Bonferroni at α = 0.05 gives 0.01 per hypothesis:

- 99% intervals for one-sided bounds (H1 (i), H2, H4 (i), H5);
- p < 0.01 for the movability null;
- a 98% interval for the TOST in H3, which is two one-sided tests each at 0.01.

H1 and H4 are intersection–union tests, so no further correction is needed within them.

**Interval types.**

- Patient-level proportions: Clopper–Pearson, 99% for decisions. Patient coverage is decided on its point estimate and its 99% Clopper–Pearson bound is reported.
- Continuous means: percentile bootstrap, 2,000 resamples.

**Verdict categories.** Supported, not supported, undecided, not reached; for H3 also not testable (degenerate) or flagged (near-degenerate).

**Secondary analyses.** 95% intervals, exploratory, not used for claims in the abstract.

**By-construction results** (Lemma 1, MINT under Proposition 2) are reported as software checks.

## 9 Failure, reporting, bugs and deviations

**Reporting.** Every primary verdict is reported. Negative, undecided, degenerate and not-reached results go into main §0x on the day they are known and into the manuscript's Results and Limitations.

**Bugs.** A bug is code whose behaviour differs from this plan or from the cited P7 code. An unwelcome result is not a bug. A bug may be shown by:

- a failing test;
- the Python–SPARQL check;
- inspection. In this case the bug must first be captured by a new failing test, added to the hashed test suite, before the corrected run (review suggestion S9).

Each fix is logged with date, description, diff hash, the results seen at the time, and values before and after.

**Script hashing.** All analysis and run scripts are hashed before the first primary run.

**Deviations.** Any other change is entered in a "Deviations from pre-registration" table, in this folder and in main §0x, with date, change, reason and the results seen at the time.

- After any primary result has been seen, primary hypotheses and thresholds do not change. A change made then is labelled post hoc, and the frozen analysis stays primary.
- Excluding patients, configurations or seeds because of their results is not allowed.

**After v3.** v3 is the final design. The fix-check that follows only confirms that Section 15 was carried out. Any further change is a deviation.

## 10 Reproducibility

**Code.** New code goes in `<local>`, `q1_domain_cvd/`, `q1_generators/` and `q1_formal/`. Results go in matching folders under `<local>`. Existing P7 code and outputs are not edited.

**Sources.** Guideline PDFs and text conversions go under `paper7/references/` with SHA-256 values.

- KDIGO PDF of the pre-plan check: b18db280f7dc889a1a99447b779c0312cd536f939a5180b38894a5d68e4410c0.
- The extraction copy must match it, or the difference is logged.

**Tables and runs.** Tables are built only from per-counterfactual result files, with numbers truncated to four decimals. Runs record the environment, seeds, and the hashes of inputs, graph export, role table and scripts.

## 11 Timeline (indicative)

| Dates (2026) | Work |
|---|---|
| 11–12/11 | v3; fix-check |
| 12–14/11 | A0: freeze and hash prompts, chunks, model settings, PDFs, text conversions; recall gate of the local model; build the NHANES CKD table (flow diagram); generate and hash the CKD role table; download NHANES laboratory and weight files |
| 14–18/11 | KDIGO extraction (two extractors), quotation check, agreement, graph export, Python and SPARQL check |
| 13–20/11 | D proofs and machine check; B porting, parity and unit tests; scripts hashed (no real-data runs) |
| 20–23/11 | A primary runs (H1–H3), then secondary |
| 23–28/11 | B runs (H4, H5), then secondary |
| 28/11–01/12 | analysis by frozen scripts; main §0x; deviations table |
| from 02/12 | manuscript |

Slippage is not a deviation. Content changes are.

## 12 Out of scope and future work

- **Longitudinal validation** (HRS, ELSA, CHARLS, or MEPS panel files) is future work.
- **Human evaluation** is excluded by project rule.
- **A second automated ADA extraction** remains excluded by ADA's terms of use.

## 13 Open questions for the student

1. Article structure: one Q1 article containing HISS v6 plus the extensions (assumed here), or HISS v6 first.
2. HEARTS module PDFs must be downloaded by hand from WHO IRIS. Without them the CVD replication is not reached. Dropping it entirely is an acceptable alternative, since it is expected to be degenerate.

Decided since v2 and no longer open:

- the cross-family local extractor (approved);
- sending KDIGO and HEARTS text to Claude (within the NC clause, Section 4.3);
- the KG release licence (CC BY-NC-SA 4.0, with the per-source quotation rule).

## 14 References

1. KDIGO CKD Work Group. KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease. Kidney Int. 2024;105(4S):S117–S314. [https://doi.org/10.1016/j.kint.2023.10.018](https://doi.org/10.1016/j.kint.2023.10.018)
2. World Health Organization. HEARTS technical package for cardiovascular disease management in primary health care. Geneva: WHO; 2016–2020. [https://www.who.int/publications/i/item/9789241511377](https://www.who.int/publications/i/item/9789241511377)
3. Wachter S, Mittelstadt B, Russell C. Counterfactual explanations without opening the black box: automated decisions and the GDPR. SSRN Electronic Journal. 2017. [https://doi.org/10.2139/ssrn.3063289](https://doi.org/10.2139/ssrn.3063289)
4. Karimi AH, Schölkopf B, Valera I. Algorithmic recourse: from counterfactual explanations to interventions. FAccT 2021. [https://doi.org/10.1145/3442188.3445899](https://doi.org/10.1145/3442188.3445899)
5. Ustun B, Spangher A, Liu Y. Actionable recourse in linear classification. FAT* 2019. [https://doi.org/10.1145/3287560.3287566](https://doi.org/10.1145/3287560.3287566)
6. Laugel T, Lesot MJ, Marsala C, Renard X, Detyniecki M. Inverse classification for comparison-based interpretability in machine learning. 2017. [https://arxiv.org/abs/1712.08443](https://arxiv.org/abs/1712.08443)
7. Pawelczyk M, Bielawski S, van den Heuvel J, Richter T, Kasneci G. CARLA: a Python library to benchmark algorithmic recourse and counterfactual explanation algorithms. 2021. [https://arxiv.org/abs/2108.00783](https://arxiv.org/abs/2108.00783)
8. Mahajan D, Tan C, Sharma A. Preserving causal constraints in counterfactual explanations for machine learning classifiers. 2019. [https://arxiv.org/abs/1912.03277](https://arxiv.org/abs/1912.03277)

**Verification.** DOIs 1, 3, 4 and 5 were checked with the Crossref API, and the arXiv identifiers with the arXiv API, on 11/11/2026.

## 15 Response to the blind reviews

**v2 review, new required fixes.**

| Fix | What changed | Section |
|---|---|---|
| N1 | Role-permutation null replaced by a per-patient movability null (exact per patient, Monte Carlo across patients, p < 0.01 reachable); O-share defined as a per-patient ratio of sums; a uniformity test of the null added to the unit tests | 2, 4.7, 4.8, 5.6 |
| N2 | Headline reframed: the graph is an audit and derivation instrument. The transfer test is H1 and H2 with mechanically derived roles. H3 became an equivalence test, expected to pass, citing P7 Table 7 and §3.2. Cross-guideline verdict agreement is key secondary with a reading rule. Near-degenerate case defined (supporting levers movable for < 10% of patients) | 1, 3, 4.1, 4.7, 4.8 |
| N3 | Indicator change sizes reported; capped reading (one GenHlth level or one PHQ-9 band per supporting lever) as secondary; stated that a supported route does not bound change size | 3, 4.7 |
| N4 | No patient below 0.5 is ever included; a floor of 50 patients, below which the result is not reached | 2, 4.6 |
| N5 | Equal search effort: published, lock and route-aware Wachter all get P runs per seed; H5 is lock against published; valid among requested defined for a one-output generator | 2, 5.3, 5.5 |
| N6 | `t_max_min` disabled as a listed edit; iteration cap only; λ rule documented; a load-independence unit test added | 5.2, 5.6 |
| N7 | (a) a failed quotation drops only that extractor's edge; (b) raw and layout text with a three-line window rule; (c) chunking frozen; (d) recall gate on HEARTS-D and MoH 5481; (e) declared that the construct table and section list were written after the KDIGO check, with no KDIGO examples in the prompts | 0, 4.4 |
| N8 | Source-construct table added; PAQ605 mismatch stated as a threat; 2021–2023-only analysis as the matched sensitivity | 4.4 |
| N9 | Measured blood pressure (≥ 130 mmHg) and cholesterol (≥ 240 mg/dL) as treatable; ever-told items immutable as sensitivity | 4.5 |
| N10 | A0 added to Proposition 1; Proposition 2 bound corrected to k ≥ 1 + t; k = 1 statement simplified; machine check covers systems without A0 | 6.2, 6.3, 6.4 |
| N11 | Pooled Cohort Equations negative control removed | 4.5 |
| N12 | Analytic sample, label rule for missing tests, pregnancy and examination exclusions, complete cases, flow diagram; reason for no weights; weighted refit as sensitivity | 4.5 |
| N13 | Full BRFSS role table and lock set given; no proxy role in the code; DiffWalk immovable; pattern count derived | 2, 5.3 |
| N14 | Clopper–Pearson intervals for patient-level proportions | 2, 8 |

**v1 review, items marked partly resolved in the v2 review.**

| Fix | What changed in v3 | Section |
|---|---|---|
| 3 | H1 (i) labelled a replication check; the informative component is the movability null; the H2 margin is stated as a convention, not justified by restating the number; H3 δ justified by grid steps | 4.8 |
| 6 | Order of writing declared (N7e); freezing extended to chunks and both text conversions | 0, 4.4 |
| 7 | Cross-family extractor approved and specified; recall gate added | 4.4 |
| 10 | Cohort floor replaces the invalid fallback (N4) | 4.6 |
| 11 | Equal search effort (N5) | 5.3 |
| 14 | Wall-clock rule removed (N6) | 5.2 |
| 16 | Proposition corrections (N10) | 6 |
| 20 | Movability null (N1) | 4.7 |

**Optional suggestions of the v2 review.**

- Taken: S1 (pre-generator flip share), S2 (weighted refit), S3 (per-cycle reports), S4 (population property and in-scope reading), S5 (CVD labelled expected-degenerate), S6 (strict k = 2 reading), S7 (expected-results table), S8 (quotation release rule reconciled with the existing export), S9 (bug by inspection needs a failing test), S10 (title wording).
- Points where the reviewer and the plan differ: none. On S8, the existing export carries MoH and HEARTS-D quotations but no ADA quotation, so it is consistent with the per-source rule of Section 4.3 and no change to the export is needed.

**Fixes of the v1 review resolved in v2** (1, 2, 4, 5, 8, 9, 12, 13, 15, 17, 18, 19) are unchanged, apart from open question 3 of v2. That question is now decided (Section 4.3).

**Edit 11/11/2026 16:45 (same day, before any run).** Blocking edit from the fix-check (`fixcheck_prereg_q1_v3_20261111_1644.md`): the claim O-A5 ≥ 0 removed in §4.7, §4.8 H3 and §6.3; H3 'not supported' now two-sided; two wording fixes (null-set size in CKD, δ wording for day counts). No result had been seen.
