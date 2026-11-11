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
