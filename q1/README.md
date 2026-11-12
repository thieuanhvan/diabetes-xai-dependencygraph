# q1: extension of P7 for a journal article (pre-registered)

Code for step A0 of the pre-registered extension (second guideline and disease: KDIGO 2024 and CKD in NHANES).
The canonical copy lives in the authors' project folder; this is a synced copy of the scripts only.
No guideline text, chunk files or survey data are included: KDIGO (CC BY-NC-ND 4.0) and NICE text stay local,
NHANES files are fetched from wwwn.cdc.gov. Paths in the scripts point to the authors' machine.

- `q1_domain_ckd/`: text units and chunks, frozen extraction prompt and settings, NHANES CKD analytic table and flow,
  graph-derived CKD role table, freeze manifest, Kaggle notebook generator, ingest script for the returned outputs.
- `q1_domain_cvd/`: BRFSS 2021 name and coverage gate for the CVD replication.
- `kaggle/`: the notebook that runs the local extractor (Qwen2.5-7B, llama.cpp b12283, CUDA).

Step A1 (KDIGO extraction agreement): the local extractor failed its recall gate, so the pre-registered fallback was
used, a second Claude instance with an independently written prompt (`extraction_prompt_v2_fallback_*.txt`,
rendered by `a1_fallback_render_prompts.py`). `a1_agreement.py` applies the frozen quotation check to both
extractors and computes kappa, PABAK, positive/negative agreement and the agreed (intersection) edge set.

Extension B (counterfactual recourse beyond the P7 counterfactual generator): `q1_ext_b/` holds the Wachter core
(unmodified CARLA commit 24db00a files under `vendor/`, MIT licence, plus the edited core with the pre-registered
changes), Growing Spheres, Actionable Recourse (own MIP) and MINT runs on BRFSS, the unit tests run before any
real-data run, the analysis script and the freeze-manifest script. No BRFSS data, models or outputs are included.

Post-hoc analysis B-P1 (`q1_ext_b/posthoc/`, exploratory, not part of H4/H5): the pre-registered MLP with seed 42
is a constant function, so H4 and H5 are not reached. With the student's approval, a post-hoc plan frozen before any
refit tries seeds 43, 44, ... of the same architecture and training (accept: every hidden layer has a live unit and
at least 50 test patients with p >= 0.5; stop at 5 accepted or 30 tried) and runs Wachter on each accepted MLP with
the unchanged extension B code. `ph_seed_screen.py`, `ph_run_wachter.py`, `ph_analysis.py`.

Third domain, hypertension (`q1_domain_htn/`, addendum HTN v1, design and data only): NHANES 2017-2023 table with a
measured-BP label (mean SBP >= 130 or DBP >= 80 mmHg) and a measured-or-treated label, graph-derived role table
(HighBP is the outcome and is removed; Income, Education and AnyHealthcare are immutable in every mode), keyword
rule for selecting guideline sections, recall-gate prompts for both Claude extractors, and the freeze-manifest
script. No guideline text, NHANES data or outputs are included. No extraction or counterfactual has been run.
