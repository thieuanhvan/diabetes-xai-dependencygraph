*Reviewer copy for anonymised review. Original SHA-256 be5308828878a1eef5c6f62338bcd3e05124afe2099e78c488216d4b8a6ff015; 40 substitutions (author and personal references, internal project codes, local paths, review records, non-English approval quotes). The unredacted original will be deposited with the artefact DOI.*

# Pre-registration addendum: a third domain, hypertension (HTN), for the dependency-graph study Q1 extension (v3)

Version v3, written 12/11/2026 from 08:40 (machine time, checked with `date`). It replaces v2 (`prereg_addendum_htn_en_v2_20261112_0829.md`, SHA-256 fc6e14d2…9848f40cb), which replaced v1 (`prereg_addendum_htn_en_v1_20261112_0739.md`, SHA-256 5a9694ff…7426ac83); both stay hashed. v1 was reviewed internally internally (revise before extraction; Section 14 maps its 12 issues). Before v2 was frozen, the authors decided (12/11/2026) that the two extractors must come from different model families (Sections 5.3 to 5.5 and 15). v2 was checked internally a second time internally (revise again, text only); v3 makes exactly the four fixes N1 to N4 asked for (Section 16). No HTN extraction output, model fit or counterfactual exists at the time of writing.

The addendum adds a third disease domain to the frozen pre-registration `preregistration_reviewer_copy.md` (SHA-256 95a83da5…112369d, "v3" below). v3 is not edited. Where this addendum is silent, v3 and the clarifications C1–C14 of `deviation_log_reviewer_copy.md` apply to HTN as they apply to CKD.

Author of the plan: Claude (Anthropic), for the authors. Decisions taken by the authors or the authors are marked as such.

## 0 Status at writing and what the author had seen

Nothing HTN-specific had been extracted, fitted or generated. Declarations:

1. **CKD results.** Before writing v1, the author read the CKD A2 results note and the KDIGO agreement file. CKD main cohort: H1 supported (O-A1 0.2102, movability-null p = 0.0036), H2 supported, H3 supported (O-A5 0.0083); less-exposed cohort: H1 undecided (p = 0.0146). KDIGO agreed graph: BMI to GenHlth, PhysActivity to MentHlth, BMI to HighBP, BMI to HighChol (κ 0.9169 over 88 Concept pairs). Thresholds are copied from v3 and were not changed after reading these numbers. The author is the same model as extractor A (Section 5.3).
2. **HTN data.** The NHANES HTN table (Section 4) was built before v1. The author saw flow counts, label prevalence per cycle and missingness: no association between any feature and the label, no model.
3. **Origin of rule R-IMM** (review issue 9). Freezing Income, Education and AnyHealthcare was not in v3. It comes from an internal pre-submission review on 12/11/2026, which flagged as a flaw that the CKD analysis lets these features move. That review was written after the CKD results existed. The rule is therefore adopted after CKD results were seen. Section 7.4 reports H1-HTN under both readings so that its effect is visible.
4. **Guideline text.** v1 was written without any text of the guideline. Between v1 and v2 the PDF arrived (Section 2.1) and the index-only stage was run (Section 5.1). The author therefore saw, before writing v2, the guideline's table of contents, all numbered headings, all table and figure captions, and the opening lines of section 4 and of Table 12 (to check the cut). No extraction prompt was run, and no route was read off the text for planning. Three v2 changes touch the unit rule after the headings were seen: the keywords "anxiety", "mood" and "mental" (decided by the authors on review issue 11); word-start matching (needed so that "mental" does not match "environmental"); and the keyword "overweight" (added so that word-start matching keeps every title that the v1 substring "weight" matched). Section 5.1 shows that none changes the selected units.
5. **Prompts and extractor B.** The two extraction prompts are the frozen CKD prompts, reused byte for byte. Nothing was written or tuned for this guideline. Extractor B (Qwen2.5-72B-Instruct) has never been run on any guideline text in this project; no output of it existed when it was chosen.

## 1 Purpose and scope

Question: does the result of the CKD domain hold for a third guideline and disease? That is, with roles derived mechanically from the graph, do generators place changes on survey health-status indicators beyond what movability explains, and does the graph-derived lock remove this cheaply (H1-HTN, H2-HTN)? Is route-aware enforcement with routes from the hypertension guideline equivalent to the lock, and is that equivalence informative (H3-HTN)?

In scope: guideline, NHANES HTN data, role table, extraction design, hypotheses and tests. Out of scope as in v3 Section 1: human raters, manual annotation, longitudinal validation. HTN is the third domain of the same the dependency-graph study article (author decision, 12/11/2026).

What HTN adds over CKD: a label that is a measured physiological state with high prevalence, and a domain in which the main treatable concept of the earlier domains (blood pressure) becomes the outcome.

## 2 Guideline and secondary authority

### 2.1 Primary guideline

**Chosen:** the 2025 AHA/ACC/AANP/AAPA/ABC/ACCP/ACPM/AGS/AMA/ASPC/NMA/PCNA/SGIM Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults (Jones DW, Ferdinand KC, Taler SJ, et al.), published simultaneously in three journals. Crossref records (checked 12/11/2026, generic client, no e-mail):

| Copy | DOI | Crossref licence record |
|---|---|---|
| JACC 2025;86(18):1567–1678 | [10.1016/j.jacc.2025.05.007](https://doi.org/10.1016/j.jacc.2025.05.007) | version of record: Elsevier user license; TDM: Elsevier TDM licence |
| Hypertension 2025;82(10) | [10.1161/HYP.0000000000000249](https://doi.org/10.1161/HYP.0000000000000249) | none |
| Circulation 2025;152(11) | [10.1161/CIR.0000000000001356](https://doi.org/10.1161/CIR.0000000000001356) | none |

**Copy used: JACC version of record,** the only copy with a stated reuse licence. The Elsevier user license permits non-commercial access, copying and text and data mining, and forbids redistribution and adaptation. It is not a Creative Commons licence. The guideline is not in PubMed Central.

**How it was obtained.** Automated requests to the publisher PDF links (curl, one request each, standard browser user-agent string) returned HTTP 403 from bot protection, and a further request to ScienceDirect was stopped by the session's permission check before it was sent. Nothing was bypassed. the authors downloaded the PDF by hand on 12/11/2026 (about 08:20): `paper7/references/q1_htn/AHA-ACC-2025-HBP-Guideline_JACC.pdf`, 8,028,657 bytes, 112 pages, journal pages 1567–1678 (PDF page = journal page − 1566), SHA-256 60f53812985f894e0d9cbc8bf3b9931c5bf6b68a15f326f70c925b751ee51482. Text conversions: pdftotext 4.00, `-raw` and `-layout`, next to the PDF, hashed in the A0-HTN manifest.

### 2.2 Licence and use

the authors accepted the Elsevier user license on 12/11/2026: use is internal and non-commercial; the PDF and any verbatim text are never redistributed.

- **(a) Automated extraction:** permitted for non-commercial purposes by the licence.
- **(b) Sending text to Claude and to a rented GPU:** as v3 Section 4.3 (b), part of the licensee's own non-commercial research use; the text is sent with its attribution and licence notice. Only rendered chunk messages go to the rented machine, never the PDF, and they are deleted there before the machine is destroyed (Section 15).
- **(c) Release:** the released KG carries no verbatim AHA/ACC text, only locator, strength, Class of Recommendation (COR), Level of Evidence (LOE) and an own-words paraphrase. The PDF, text conversions, units, chunks and rendered prompts are never pushed to any repository.

### 2.3 Secondary authority for cross-guideline agreement

**KDIGO 2024 is the secondary authority for A-Q4-HTN; ADA 2026 is an additional comparison.** Reasons: KDIGO's graph was built with the same two-extractor, quotation-checked protocol and vocabulary, so differences reflect guidelines rather than ways of building edges; KDIGO covers blood pressure and lifestyle (§3.2–3.4); ADA cannot be re-extracted (v3 Section 12). Limitation: KDIGO addresses people with CKD (371 of 9,944 HTN participants report kidney disease); its edges are read without population scope here.

## 3 Domain, roles and lock set

**Derivation.** v3 Section 3 steps 1–4, run by `a0_role_table_htn.py`, plus two domain rules applied by the same script:

- **R-OUT.** The Concept measured by the outcome (BLOOD_PRESSURE) is the domain outcome. It is not a feature and has no role in HTN. HighBP is removed.
- **R-IMM.** Every feature whose role is immutable has direction immutable in every generator mode. Income, Education and AnyHealthcare, movable upward in CKD, are frozen. Origin: Section 0, item 3.

**Role table** (SHA-256 f1a6b6d1…f876a94302; lock set 78c013db…431ea0095, identical to the CKD lock set):

| Feature | Concept | NHANES source | Role | Direction | How derived |
|---|---|---|---|---|---|
| Diabetes | DIABETES_HISTORY | `DIQ010` = 1 | immutable | immutable | new Concept, rule: diagnosis history |
| HighChol | CHOLESTEROL | `LBXTC` ≥ 240 mg/dL (measured) | treatable | down | inherited |
| BMI | BODY_WEIGHT | `BMXBMI`, integer | lever | bidirectional | inherited |
| Smoker | SMOKING | `SMQ020` = 1 and `SMQ040` in {1, 2} | lever | down | inherited |
| PhysActivity | PHYSICAL_ACTIVITY | 2017–2020 `PAQ605`; 2021–2023 `PAD790Q/U`–`PAD820`, moderate + 2 × vigorous ≥ 150 min/week (O1-res) | lever | up | inherited |
| GenHlth | GENERAL_HEALTH | `HUQ010` | indicator | down | inherited |
| MentHlth | MENTAL_HEALTH | PHQ-9 total in the dependency-graph study bands | indicator | down | inherited |
| Stroke | STROKE_HISTORY | `MCQ160F` | immutable | immutable | inherited |
| HeartDiseaseorAttack | CHD_MI_HISTORY | `MCQ160C` or `MCQ160E` | immutable | immutable | inherited |
| KidneyDisease | KIDNEY_DISEASE_HISTORY | `KIQ022` = 1 | immutable | immutable | new Concept, rule: diagnosis history |
| Age, Sex | AGE, SEX | `RIDAGEYR`, `RIAGENDR` | immutable | immutable | inherited |
| Education, Income, AnyHealthcare | EDUCATION, INCOME, HEALTH_COVERAGE | `DMDEDUC2`, `INDFMPIR` (5 bands), `HIQ011` | immutable | immutable | inherited role; R-IMM sets direction |
| Cycle | SURVEY_CYCLE | 0 = 2017–2020, 1 = 2021–2023 | immutable | immutable | new Concept, rule: survey design |

**Lock set:** {GenHlth, MentHlth}. **Movable set for the null:** {HighChol, BMI, Smoker, PhysActivity, GenHlth, MentHlth}; at most C(6, 2) = 15 subsets per patient.

**Movable for a patient** (review issue 4; used by the null, the near-degenerate check and Section 7.3): feature f is movable for patient i if its permitted direction allows at least one grid step from the patient's value x_if that stays inside the taxonomy study range of f. An immutable feature is never movable.

**Diagnosis histories** (review issue 8). Diabetes, KidneyDisease, Stroke and HeartDiseaseorAttack are kept as immutable prognostic covariates. They partly lie downstream of blood pressure and are linked to treatment by indication, so they carry outcome information, but none is derived from blood pressure or BP medication. `BPQ020`, `BP_med_now` and `BPQ080` are never features. A refit without the four diagnosis histories is a sensitivity analysis (Section 7.4). CKD enters as self-reported `KIQ022`, not as the measured eGFR/ACR label of the CKD domain (laboratory completeness would remove participants, and the measured state is partly a consequence of blood pressure).

**Role-conflict check.** As v3 Section 3 step 5.

## 4 Data, cohort and labels (A0-HTN)

**Source and code** (review issue 5). NHANES 2017–2020 (`P_` files) and 2021–2023 (`_L` files), the raw files and recoders of the CKD table. The nhanes-diabetes changes that were uncommitted at v1 (a held-out 2015–2016 cycle added to `download_raw.py`, `cycle_loader.py`, `year_configs.py`) are now committed as **89af37c** (code only). The table was rebuilt at 89af37c with a clean source tree: the analytic CSV has the same SHA-256 (e8efa0d3…44642718), and both flow files are unchanged. Check: the rebuilt the dependency-graph study features equal the dependency-graph study's NHANES tables (0 mismatches on 14 features).

**Where `KIQ022` and `LBXTC` come from.** They are not in the dependency-graph study's tables. `a0_nhanes_htn.py` reads `P_KIQ_U.xpt` / `KIQ_U_L.xpt` and `P_TCHOL.xpt` / `TCHOL_L.xpt` from `paper7/data_q1/nhanes_raw/<cycle>/` (downloaded from wwwn.cdc.gov in CKD A0, hashed in the CKD A0 manifest) and merges them one-to-one on `SEQN`. Since v2 the gate file `a0_gate_nhanes_htn.json` records each file's path and SHA-256 under `extra_tables`.

**Analytic sample**, in order: (1) age ≥ 20; (2) `RIDSTATR` = 2; (3) `RIDEXPRG` ≠ 1; (4) primary label available; (5) complete cases on all 16 features.

**Primary label L1 (measured).**

- Readings `BPXOSY1`–`3` and `BPXODI1`–`3` (`P_BPXO`, `BPXO_L`). A pressure (systolic or diastolic) is available when it has at least two valid readings; its value is their mean.
- Positive if an available systolic mean is ≥ 130 or an available diastolic mean is ≥ 80 mmHg, whether or not the other pressure is available. Negative only if both pressures are available and both are below. Missing otherwise (so: one pressure available and below threshold, the other unavailable, is missing; count 0 in both cycles).
- **Why L1 is primary** (review issue 6). The recourse question is what a person could change so that the measured state the model reads changes; lever changes act on measured blood pressure. A treated person whose blood pressure is controlled is, for that question, in the negative state. L2 treats such a person as positive whatever they change, so its counterfactuals would mostly have to "un-treat" an unchangeable history. L2 is the epidemiological convention and is kept as a secondary refit.
- What L1 is not: a diagnosis (that needs two or more occasions). 130/80 at one visit over-calls hypertension relative to a diagnosis. 3,001 analytic participants report current BP medication. The model detects current state, not risk.

**Secondary label L2 (measured or treated).** L1 positive, or now taking prescribed BP medicine. Negative if L1 is negative and medication use is known to be no. Missing otherwise.

- **Routing differs by cycle** (review issue 7). 2017–2020: `BPQ050A` ("now taking") is asked only when `BPQ040A` = 1 ("told to take a prescription"), which is asked when `BPQ020` = 1; a person told of high BP but never told to take medicine is coded "no". 2021–2023: `BPQ_L` has neither `BPQ040A` nor `BPQ050A`; `BPQ150` ("now taking") is asked of everyone with `BPQ020` = 1. The check is L2 prevalence by cycle: 0.5571 and 0.5448 (Table below); per-cycle results are reported for every L2 analysis.

**Less-exposed cohort.** Participants with `BPQ020` = 1 are removed from the cohort, with the same fitted model and cohort rule (C10; missing counted as not told).

**Counts** (analytic sample; shares truncated to four decimals):

| | 2017–2020 | 2021–2023 | Pooled |
|---|---|---|---|
| after steps 1–3 | 8,457 | 6,023 | 14,480 |
| L1 missing | 895 | 205 | 1,100 |
| L1 available | 7,562 | 5,818 | 13,380 |
| analytic sample | 5,887 | 4,057 | 9,944 |
| L1 positive | 2,588 (0.4396) | 1,675 (0.4128) | 4,263 (0.4287) |
| L2 positive / available | 3,279 / 5,885 (0.5571) | 2,210 / 4,056 (0.5448) | 5,489 / 9,941 (0.5521) |
| told high BP (`BPQ020` = 1) | 2,263 (0.3844) | 1,488 (0.3667) | 3,751 (0.3772) |
| now taking BP medication | 1,770 | 1,231 | 3,001 |
| less-exposed sample | 3,624 | 2,569 | 6,193 |
| L1 prevalence, less-exposed | 0.3283 | 0.3188 | 0.3243 |

**Missingness** among label-available participants: Income 0.1288 and 0.1289; MentHlth 0.0428 and 0.1158; HighChol 0.0637 and 0.0904; all others below 0.01. Any feature missing: 0.2215 and 0.3026. Complete cases; no imputation. Survey weights not used (v3 Section 4.5); weighted refit as sensitivity.

## 5 Extraction design

### 5.1 Units: rule and index-only result

**Rule** (`section_rule_htn_v2.json`, applied by `a0_build_chunks_htn.py`):

- Main body only, from the first numbered section to the reference list.
- A numbered heading at any level whose title contains a keyword defines a unit with its subsections. Matching is case-insensitive and word-start: the keyword must begin a word of the title.
  - Levers and behaviours: nonpharmacolog, non-pharmacolog, lifestyle, weight, overweight, obes, diet, nutrition, sodium, potassium, physical activity, exercise, fitness, alcohol, tobacco, smoking, nicotine, stress, sleep.
  - Health status: quality of life, well-being, wellbeing, depress, mental health, psycholog, cognit, dementia, brain health, functional, patient-reported, anxiety, mood, mental.
- A TABLE or FIGURE whose caption contains a keyword is also a unit, cut from `-layout` (clarification HTN-C3).
- **Limit on the index-only stage** (review issue 11). Footer regexes, body limits, table-of-contents reconciliation and the caption cut are clarifications. They cannot add or remove a unit beyond what the keyword rule yields when applied to the reconciled heading index (the printed contents plus the level-4 children of accepted entries, clarification HTN-C2) and to the captions.
- If no heading matches, the graph is empty (degenerate); nothing is added by hand.

**Index-only result** (run 12/11/2026, before v2; clarifications HTN-C1 to HTN-C3 in the deviations log):

- Body: PDF pages 8–80 (from "1. INTRODUCTION" to the line before "R E F E R E N C E S" on page 81). Three header/footer lines removed on every body page (73 of 73).
- Headings: all 56 entries of the printed table of contents (PDF page 3) found in the body, plus 11 level-4 headings (the contents list three levels). 258 numbered lines that are not headings (recommendation numbers, supportive-text items, COR/LOE cells) were rejected by the reconciliation rule. One heading, 5.2.1, is worded "Pharmacologic" in the body and "Pharmacological" in the contents; it is accepted by its number and first two words.
- Captions: 35 tables and figures in the body; one matches.
- **Selected units (5):**

| Unit | Source | PDF pages | Keywords | Size (characters) |
|---|---|---|---|---|
| 3.2.3.3 Obstructive Sleep Apnea | raw | 30 | sleep | 3,781 |
| 5.1 Lifestyle and Psychosocial Approaches | raw | 31–35 | lifestyle | 20,218 |
| 5.3.2 Obesity and Metabolic Syndrome | raw | 50–51 | obes | 5,577 |
| 5.3.9.4 Mild Cognitive Impairment and Dementia | raw | 59–60 | cognit, dementia | 3,553 |
| Table 12 Lifestyle and Stress Reduction Interventions to Lower Blood Pressure | layout | 33 | lifestyle, stress | about 5,500 |

  Table 12 also lies inside the 5.1 unit, so it is seen twice (as Tables 37–38 in CKD). The number of chunks is fixed at stage 2 by the tokeniser; the character counts suggest five to seven.
- Effect of the v2 keyword changes: none on the selection. Under v1 substring matching with "mental" added, Table 8 ("Environmental, Behavioral, and Genetic Causes of Hypertension") would have matched; word-start matching prevents that. No heading or caption contains "anxiety" or "mood".
- Not selected under the rule (declared, not changed): 4 "Prevention Strategies" (a one-paragraph synopsis that refers to 5.1), 5.2.5 adherence strategies, 5.4 plan of care. Routes stated only there are not extracted.

### 5.2 Chunking

As CKD (C1): at most 6,000 tokens, 500-token overlap, line-snapped, Qwen2.5 GGUF vocabulary through llama.cpp b12283 `/tokenize` (tokeniser only). Same chunk files for both extractors. The tokeniser vocabulary is that of the Qwen2.5 family, so B sees the same token counts; A's tokeniser differs, which only affects chunk length as A counts it.

### 5.3 Extractors and run policy

The two extractors come from different model families (author decision, 12/11/2026). Both are large language models.

- **Extractor A: Claude** (`claude-opus-5-5`), frozen CKD prompt v1 (system 2959ef9d…; user template 960a8261…). Each chunk goes to a fresh agent sub-session that sees only its system prompt and rendered user message. Temperature and length cannot be controlled (as D2). The author of this plan is the same model; this is disclosed.
- **Extractor B: Qwen2.5-72B-Instruct**, frozen CKD prompt v2 (system 3a38d58b…; user template 8e9c4a25…), written without opening v1 (event E1). Ungated, Qwen licence; no account or login is used.
  - Weights: `Qwen/Qwen2.5-72B-Instruct-AWQ`, Hugging Face revision `698703eae6604af048a3d2f509995dc302088217` (4-bit AWQ, 11 safetensors files, 41,607,438,677 bytes in the repository). File hashes are taken from the Hugging Face listing at that revision and checked after download.
  - Runtime: vLLM 0.32.0, Docker image `vllm/vllm-openai:v0.32.0` pinned by digest `sha256:6ee133356d49ed24cee03dd0cda3d3980279a11c107ce3e752c89e76540f41c9`; quantisation `awq_marlin`; `--max-model-len 16384`, `--max-num-seqs 1`, `--no-enable-prefix-caching` (so no request reuses cached keys and values of an earlier one), `--seed 42`, `--generation-config vllm` (so the model's own sampling defaults are not applied).
  - Hardware: one GPU class only, NVIDIA A100 80 GB (Section 15). GPU model, driver version, CUDA version and vLLM version are logged at start (`nvidia-smi`, `vllm --version`) with the outputs. Reproducibility of B's outputs is claimed only for the same image digest, weights revision and GPU class.
  - Requests: OpenAI chat-completions endpoint, system and user message as rendered, sent one at a time; `temperature` 0 (greedy), `top_p` 1, `top_k` −1, `repetition_penalty` 1, `seed` 42, `max_tokens` 4096; no constrained decoding. `finish_reason` and token counts are saved for every request; a response with `finish_reason` = `length` (cut at 4,096 tokens) counts as zero edges for that chunk, is never retried, and is reported. A chunk whose rendered prompt exceeds 16,384 − 4,096 tokens stops the run (none is expected: chunks are at most 6,000 tokens).
- Vocabulary: the frozen 12-Concept list (6db9963a…). HTN item map: `concepts_constructs_htn_v1.json`. Edges with BLOOD_PRESSURE at either end are kept in the KG as routes to the outcome, but are not used by the audit; a path through BLOOD_PRESSURE does not count for k = 2.
- Neither extractor sees the other's prompt or output, this addendum, the CKD results or any role table.
- **Run policy** (review issue 1; authors decision):
  - exactly one run per chunk and extractor, for gate chunks and HTN chunks alike;
  - at most one retry, only for a technical failure (empty response, timeout, tool or session error with no model text);
  - an output that is returned but cannot be parsed counts as zero edges and is never retried;
  - every attempt is saved with its time, the reason for any retry and its SHA-256;
  - any other re-run of a chunk, a gate or a pass is a deviation.

### 5.4 Recall gate

Before any HTN chunk is extracted, both extractors run once on the 18 frozen recall-gate chunks of the CKD freeze (hash-checked; extractor A with the frozen v1 messages, extractor B with the v2 messages rendered by `a0_render_gate_prompts_v2.py`). Pass rule for each extractor: the HEARTS-D agreed edge and at least 3 of the 5 MoH 5481 agreed edges recovered after the quotation check; NG28 output reported as false positives. Extractor B must pass the same gate as A. **If either fails, there is no fallback:** no new prompt, model, quantisation or runtime is tried; the HTN agreed graph, H3-HTN and A-Q4-HTN are "not reached"; the passing extractor's quotation-checked edges are reported descriptively as a single-extractor graph; H1-HTN and H2-HTN run unchanged.

### 5.5 Quotation check, inter-model agreement gate and graph

- **Verbatim quotation.** An agreed edge needs, for each extractor, at least one quotation that passes the scripted quotation check (v3 Section 4.4, C5) against the frozen `-raw` and `-layout` text of the JACC PDF.
- **Inter-model agreement** (review issue 3). The extractors are two model families with two independently written prompts, so agreement is between models and prompts together; the two sources cannot be separated. Both are LLMs, so errors shared by LLMs are not excluded. **Passing the gate does not show that the extraction is valid.**
- **Gate unit** (review issue 2): the 70 audit-relevant Concept pairs, i.e. the 88 candidate pairs (C7) minus the 18 with BLOOD_PRESSURE at either end (7 sources × 11 targets − 7 self-pairs = 70). All 88 are reported as secondary. Statistics: Cohen's κ, PABAK, positive and negative agreement; also on the 20 HTN item pairs.
- **Gate:** κ ≥ 0.40 and positive agreement ≥ 0.50 over the 70 pairs (Landis–Koch lower bound of "moderate"; positive agreement guards against κ driven by pairs neither extractor finds; both are conventions). If it fails, the intersection graph is reported but H3-HTN is "not testable: agreement gate failed" and A-Q4-HTN is descriptive. If neither extractor finds any of the 70 pairs, κ is undefined and the graph is degenerate.
- **Same-prompt test–retest.** A fixed random 10% of HTN chunks (at least one), drawn once at stage 2 with `default_rng(20261111)` over the chunk index and hashed before any extraction, is run a second time by each extractor: A in a fresh sub-session, B as a second request on the same server after all first runs. Reported: per extractor, run-1 versus run-2 agreement over the 70 pairs on those chunks, beside the between-model agreement on the same chunks. Descriptive, no gate; the second run never enters the graph. B is greedy and prefix caching is off, so its retest checks that the runtime is reproducible on the same machine.
- **External checks.** No human audit (project rule: no human raters). The check outside the two extractors is the scripted word-for-word quotation check against the PDF text. The descriptive local Qwen2.5-7B third extractor of the draft is dropped.
- **Graph:** intersection; union secondary; agreed strength = weaker of the two (C8).

### 5.6 Grading for evidence-support scores (secondary)

COR 1 with LOE A 0.9; COR 1 with LOE B-R or B-NR 0.7; COR 1 with LOE C-LD or C-EO 0.5; COR 2a or 2b 0.3; table entry or explicit ungraded statement 0.6; narrative 0.2. A COR 3 statement does not support an edge.

## 6 Models, generators, cohort and seeds

- Split: stratified 80/20 on L1, seed 42. Primary model: XGBoost, the taxonomy study configuration, threads unchanged; no HTN script sets OMP_NUM_THREADS.
- Features: the 16 of Section 3, in role-table order; the taxonomy study ranges as C13 (a); KidneyDisease immutable (0, 1).
- Cohort: test patients with p ≥ 0.5, at most the 200 highest-risk; fewer than 50 means H1-HTN to H3-HTN are not reached; no patient below 0.5.
- S1 (single non-indicator flip share) computed after the fit and before any generator.
- Generators: DiCE random (published, lock, route-aware with regeneration seed + 100,000·r, at most 8 rounds) for H1-HTN and H2-HTN; exhaustive sparse search (published, lock, route-aware, capped) for H3-HTN. R-IMM holds in every mode. DiCE genetic, LR and Random Forest secondary.
- Route-aware primary reading: k = 1, 𝒜 = {AHA/ACC 2025}, 𝒮 = all.
- Seeds: split 42; generators 42, 123, 2024, 7, 31337; bootstrap, permutation, Monte Carlo and test–retest draw 20261111.
- Compute: CPU, below-normal priority, at most one heavy HTN process. Extractor B runs on one rented GPU (Section 15).

## 7 Outcomes and hypotheses

Metric definitions: v3 Section 2 with C9 and C11.

### 7.1 Primary outcomes (pooled NHANES, L1, XGBoost, derived roles)

- **O-A1-HTN:** fully unactionable share, published mode, DiCE random.
- **O-A2-HTN:** per-patient movability null of v3 Section 4.7, with M_i = the features movable for patient i (Section 3 definition) under R-IMM; exact per patient (at most 15 subsets), 100,000 Monte Carlo draws, seed 20261111, p = (1 + #{T* ≥ T}) / 100,001, ties against the hypothesis.
- **O-A3-HTN:** valid among requested, lock minus published, DiCE random, with lock coverage.
- **O-A5-HTN:** per-patient difference in normalised L1 distance of the best counterfactual, lock minus route-aware, exhaustive search; can be negative.

### 7.2 Hypotheses (decision rules copied from v3 H1–H3)

| ID | Statement | Decision rule |
|---|---|---|
| H1-HTN | derived roles reproduce the failure | (i) one-sided lower 99% bound of O-A1-HTN > 0.10; and (ii) movability-null p < 0.01. Not supported if upper bound ≤ 0.10 or p ≥ 0.5; undecided otherwise |
| H2-HTN | derived lock is cheap | one-sided lower 99% bound of O-A3-HTN > −0.05 and lock coverage ≥ 0.95. Not supported if upper bound < −0.05 or coverage < 0.95; undecided otherwise |
| H3-HTN | route-aware is equivalent to the lock | TOST α = 0.01: 98% bootstrap interval of mean O-A5-HTN inside (−0.05, 0.05) is supported; lower bound ≥ 0.05 or upper bound ≤ −0.05 is not supported; undecided otherwise |

δ = 0.05 keeps v3's domain-free justification (one GenHlth step 0.25; a binary feature 1; one PHQ-9 band at least 5/30; about 0.8 BMI units).

### 7.3 Degenerate, near-degenerate, uninformative and gate cases for H3-HTN

- **Degenerate:** no agreed edge from a lever into GenHlth or MentHlth (BLOOD_PRESSURE edges do not count). H3-HTN is "not testable: degenerate graph".
- **Near-degenerate:** edges into an indicator exist, but every supporting lever is movable (Section 3 definition) for fewer than 10% of cohort patients. Computed before any generator runs. H3-HTN is flagged and not counted as evidence about the graph.
- **Equivalent, uninformative** (review issue 4; defined now, computed after the exhaustive search): fewer than 5% of cohort patients have a best route-aware counterfactual that differs from their best lock counterfactual. "Differs" means a different rounded point, or a counterfactual in one mode only. If H3-HTN is supported and this flag holds, the verdict is reported as "supported, equivalent but uninformative": equivalence then follows from the graph rarely mattering, not from the routes.
- **Gate cases:** recall gate failed gives "not reached"; agreement gate failed gives "not testable: agreement gate failed".

### 7.4 Secondary (95% intervals, exploratory)

- O-A4-HTN, change sizes, capped reading, leakage under all readings, touch share, route-aware cost, exhaustive costs, distinct counterfactuals, local outlier factor, evidence-support scores, Python–SPARQL check (100% agreement required; a disagreement is a bug).
- Readings: k = 2 permissive and strict; 𝒜 = {AHA/ACC, KDIGO}, {AHA/ACC, KDIGO, ADA}, {KDIGO}, {ADA}; graded only (COR and LOE present); in-scope (an edge whose stated population names hypertension or high blood pressure applies only to cohort patients with L1 = 1).
- **A-Q4-HTN (key secondary):** indicator-touching counterfactuals, published mode, DiCE random and exhaustive; verdicts under {AHA/ACC} and {KDIGO} at k = 1; raw agreement and κ with 95% patient-cluster bootstrap intervals; v3 reading rule (≥ 0.80 carries across, < 0.60 guideline-specific). The same against {ADA} beside it.
- **R-IMM comparison** (review issue 9): the full H1-HTN computation, both components with the H1 decision rule applied descriptively, under the CKD-comparable reading (Income, Education and AnyHealthcare movable upward in the generator and in M_i, up to 9 movable features) beside the primary reading. Also O-share.
- **Label and sample:** L2 refit (per-cycle results reported, Section 4); refit excluding participants now taking BP medication (`BP_med_now` = 1, n 6,943 before the split); less-exposed cohort.
- **Features:** refit without the four diagnosis histories (Diabetes, KidneyDisease, Stroke, HeartDiseaseorAttack); Diabetes borderline coding; role-conflict sensitivity.
- **Cycles and weights:** per-cycle O-A1-HTN and O-share; 2021–2023-only refit (matched PhysActivity construct); weighted refit.
- Edge-permutation null (1,000 permutations).
- Extraction: all-88-pair agreement, test–retest (Section 5.5).

## 8 Statistics and multiplicity

H1-HTN, H2-HTN and H3-HTN form a new family of three, separate from the v3 family of five. Each is tested at α = 0.01 (family-wise error at most 0.03; conservative against Bonferroni for three), the same scale as CKD. H1-HTN is an intersection–union test. Verdict categories as v3 Section 8, plus "not testable: agreement gate failed" and "supported, equivalent but uninformative".

**Power caveat** (review issue 12). The floor of 50 patients is weak: with O-A1-HTN near 0.20 and n = 50, the lower one-sided 99% bound is about 0.07, so H1-HTN (i) would almost certainly be undecided. The cohort is expected to be near the cap of 200 given an L1 prevalence of 0.4287, but this is not guaranteed.

**Conditional inference** (review issue 12). All bootstrap intervals and the movability null are conditional on one train–test split (seed 42) and one fitted model. They do not include split-to-split or refit variability, and the paper says so.

## 9 Expected results, stated before any HTN run

| Hypothesis | Expected | Basis |
|---|---|---|
| H1-HTN (i) | likely pass | CKD O-A1 0.2102; the dependency-graph study NHANES 19.07–22.85%. R-IMM may raise the indicator share |
| H1-HTN (ii) | uncertain | CKD p = 0.0036 (main), 0.0146 (less-exposed). R-IMM shrinks the null set, which also raises the null mean |
| H2-HTN | likely pass | CKD and the dependency-graph study |
| H3-HTN | supported, possibly flagged uninformative, or not testable (degenerate) | the selected units are lifestyle-centred and most routes may end at blood pressure |
| A-Q4-HTN | uncertain | no AHA/ACC edge known |

Further threat: blood pressure depends strongly on age (immutable), so the cohort will be older and S1 may be lower than in CKD.

## 10 Deviations

The rules of v3 Section 9 apply. For HTN, each of the following, made after this addendum is hashed, is a deviation, logged in `deviation_log_reviewer_copy.md` and main §0x with date, reason and results seen:

- any change to the labels, thresholds, reading rules, cohort or less-exposed rule, feature set or role table (`--check` must report UNCHANGED before the fit);
- any change to the keyword list, matching rule, heading rule, body limits, chunking rule, prompts, vocabulary, recall gate, agreement gate or test–retest sample;
- any re-run of an extractor outside the run policy of Section 5.3, or a new prompt after any gate result;
- a change of extractor model id, weights revision, quantisation, runtime or its version, image digest, server or decoding settings of Section 5.3, or GPU class (review issue 10);
- a rental for extractor B beyond the one further rental allowed in Section 15, or a re-request of a response that was returned;
- a change of split, seeds, XGBoost configuration, cohort threshold or cap, or the n ≥ 50 rule (review issue 10);
- a change of the secondary authority (KDIGO), of the COR/LOE scores, or of the A-Q4 reading rule (review issue 10);
- dropping any secondary analysis listed in Section 7.4 (review issue 10);
- using a PDF other than the JACC version of record with journal pages 1567–1678 and the SHA-256 of Section 2.1, including an accepted manuscript, an uncorrected proof, or the Hypertension or Circulation copy, or the 2017 guideline (review issue 10);
- running HTN steps in another order than: index-only stage and logged clarifications (done); stage-2 chunks and test–retest draw frozen and appended to the A0-HTN manifest; recall gate; extraction; quotation check and agreement; model fit, cohort and S1; near-degenerate check; generators; uninformative flag; analysis.

Clarifications (implementation choices left open, logged before the step that uses them) are not deviations, within the limit of Section 5.1. Slippage in time is not a deviation.

## 11 Open questions for the authors

None blocking. Decided on 12/11/2026: the Elsevier user license is acceptable (internal, non-commercial, no redistribution); HTN is the third domain of the same article; the extractors come from two model families, Claude and Qwen2.5-72B on a rented GPU (budget cap 8 USD); the CKD R-IMM question went to the manuscript revision.

## 12 Files and hashes

- Code: `<local path>` (synced to `diabetes-xai-dependencygraph/q1/q1_domain_htn/`, code only).
- Outputs: `paper7/outputs/q1_domain_htn/` (`a0_nhanes_htn/`, `a0_role_table/`, `a0_freeze/` including `heading_index.json`).
- Design files: `section_rule_htn_v2.json`, `extraction_settings_htn_v3.json` (v1 and v2 files kept and hashed), `concepts_constructs_htn_v1.json`.
- Freeze manifest: `outputs/q1_domain_htn/a0_freeze/A0_HTN_the authors' hash manifest`, stage 1 plus the appended blocks "A3-HTN-v2" (PDF, text conversions, heading index, v2 design files, updated scripts, rebuilt gate file) and "A3-HTN-v3" (extractor settings v3). Its hash and this addendum's hash are in `prereg/the authors' hash manifest`.
- nhanes-diabetes commit 89af37c.

## 13 References

1. Jones DW, Ferdinand KC, Taler SJ, et al. 2025 AHA/ACC/AANP/AAPA/ABC/ACCP/ACPM/AGS/AMA/ASPC/NMA/PCNA/SGIM Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults. J Am Coll Cardiol. 2025;86(18):1567–1678. [https://doi.org/10.1016/j.jacc.2025.05.007](https://doi.org/10.1016/j.jacc.2025.05.007)
2. The same guideline, Hypertension. 2025;82(10). [https://doi.org/10.1161/HYP.0000000000000249](https://doi.org/10.1161/HYP.0000000000000249)
3. Whelton PK, Carey RM, Aronow WS, et al. 2017 ACC/AHA/AAPA/ABC/ACPM/AGS/APhA/ASH/ASPC/NMA/PCNA Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults. Hypertension. 2018;71(6):e13–e115. [https://doi.org/10.1161/HYP.0000000000000065](https://doi.org/10.1161/HYP.0000000000000065)
4. KDIGO CKD Work Group. KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease. Kidney Int. 2024;105(4S):S117–S314. [https://doi.org/10.1016/j.kint.2023.10.018](https://doi.org/10.1016/j.kint.2023.10.018)
5. Landis JR, Koch GG. The measurement of observer agreement for categorical data. Biometrics. 1977;33(1):159–174. [https://doi.org/10.2307/2529310](https://doi.org/10.2307/2529310)

**Verification.** DOIs 1–3 and 5 checked with the Crossref API on 12/11/2026; DOI 4 on 11/11/2026 (v3).

## 14 Response to the internal review of v1

| Issue | Change in v2 | Section |
|---|---|---|
| 1 Critical: re-runs not a deviation | One run per chunk and extractor; at most one retry for technical failure only; unparseable = zero edges, not retried; all attempts logged and hashed; other re-runs are deviations | 5.3, 10 |
| 2 Major: gate over unused pairs | Gate on the 70 pairs without a BLOOD_PRESSURE end; all 88 secondary | 5.5 |
| 3 Major: same-model extractors | Extractor B changed to a different family (Qwen2.5-72B-Instruct AWQ, pinned revision, vLLM, greedy); B must pass the recall gate, no fallback; measure called inter-model agreement, both LLMs, gate does not show validity; same-prompt test–retest on a seeded 10% of chunks for both; no human audit (project rule); verbatim quotation required per extractor for an agreed edge | 5.3, 5.4, 5.5, 15 |
| 4 Major: uninformative H3 | "Equivalent, uninformative" flag at < 5% of patients whose best route-aware counterfactual differs from the lock's; "movable for a patient" defined | 3, 7.3 |
| 5 Major: code state | nhanes-diabetes changes committed (89af37c); table rebuilt with identical CSV hash; `KIQ022` and `LBXTC` sources stated and hashed in the gate file | 4 |
| 6 Minor: L1 | Rationale for L1; secondary refit excluding current BP medication; rule for one pressure available | 4, 7.4 |
| 7 Minor: L2 routing | Routing difference stated; per-cycle L2 prevalence as the check; per-cycle L2 results | 4 |
| 8 Minor: leakage | Diagnosis histories stated as prognostic covariates; refit without them | 3, 7.4 |
| 9 Minor: R-IMM | Origin declared; H1-HTN reported under both readings | 0, 7.4 |
| 10 Minor: deviation list | Five items added | 10 |
| 11 Minor: index-only stage | Clarifications cannot change units beyond the keyword rule on the printed contents and captions; anxiety, mood, mental added; word-start matching | 0, 5.1 |
| 12 Minor: statistics | Power caveat at n = 50; inference conditional on one split and one model | 8 |

## 15 GPU run plan for extractor B and cost estimate

Order (no step starts before the previous one ends): (1) this addendum frozen and checked a second time blind; (2) stage-2 chunks and test–retest draw frozen; (3) recall gate for A and B; (4) HTN extraction A and B; (5) test–retest runs. Steps 3 to 5 for B use one rental.

- **Provider and access.** Vast.ai, through the `vastai` command-line tool and SSH key already set up; the API key is never read or printed.
- **Offer rule.** One GPU of one class only, NVIDIA A100 80 GB (SXM4 or PCIe; x86-64 host), verified host, reliability above 0.98, download speed above 500 Mbps, disk at least 150 GB, `inet_down_cost` at most 0.005 USD/GB, total price at most 1.60 USD/h. Cheapest matching offer at rent time. Example on 12/11/2026 08:40: offer 58320599, A100 SXM4 80 GB, Czechia, 1.001 USD/h, `inet_down_cost` 0.0026 USD/GB, 2,142 Mbps.
- **Data moved.** In: the Docker image (about 9.2 GB), the weights (41.6 GB, downloaded on the host from Hugging Face), the rendered user messages and the two system prompts (a few hundred kB). Out: response JSON files only. Download charges at 0.0026 USD/GB: about 0.14 USD.
- **Time.** About 0.5 h to start, pull and load; about 27 requests for B (18 gate chunks, about 6 HTN chunks, 1 to 2 retest chunks), each up to 4,096 output tokens at an expected 20 to 30 tokens/s, under 1 h; 0.25 h to copy back and check. Estimate 1.5 h, about 1.6 USD on the example offer.
- **Cost cap.** the authors approved a few USD with a hard cap of 8 USD in total. The instance is destroyed at the latest after 4 h or when the projected total reaches 6 USD, whichever comes first, whatever has finished. The 8 USD cap covers all rentals together.
- **Requests that never returned.** A request that returned no output (no response, empty response, timeout, server error) is a technical failure under the run policy (Section 5.3). At most **one further rental** is allowed, with the same image digest, weights revision, server and decoding settings and GPU class; its hardware is logged as above. Only the requests that never returned are sent on it. A response that was returned, including a truncated or unparseable one, is never requested again. If requests are still missing after the further rental, extractor B is "not reached": the HTN agreed graph, H3-HTN and A-Q4-HTN are "not reached" as for a failed recall gate (Section 5.4).
- **Close-down.** Responses are copied back and their SHA-256 checked against hashes computed on the instance; then the chunk messages and prompts are deleted on the instance; then `vastai destroy instance <id> -y`; then `vastai show instances` must be empty. Rental id, offer, start and end times and cost are logged with the outputs.

## 16 Response to the second internal check (v2)

| Issue | Change in v3 | Section |
|---|---|---|
| N1 Major: determinism of B | `--no-enable-prefix-caching` added beside `--max-num-seqs 1`; GPU model, driver, CUDA and vLLM versions logged; reproducibility claimed only for the same image, weights and GPU class; offer rule narrowed to one GPU class (A100 80 GB); `finish_reason` saved, a response cut at 4,096 tokens counts as zero edges and is reported | 5.3, 5.5, 15 |
| N2 Major: second rental | At most one further rental with the same image digest, weights revision, settings and GPU class; only requests that never returned are sent; a returned response is never re-requested; hardware logged; still missing means B "not reached"; added to the deviation list | 10, 15 |
| N3 Minor: third extractor | Mentions removed from Sections 7.4 and 10 | 7.4, 10 |
| N4 Minor: index-stage limit | Limit phrased on the reconciled heading index (printed contents plus level-4 children of accepted entries) and captions; "overweight" declared in Section 0 item 4 | 0, 5.1 |
