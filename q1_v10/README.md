# q1_v10: code as run for the re-analysis on the shared dataset (deviation D-P5)

After the first complete analysis (code in `../q1/`, results in `../eswa2026/results/`), every BRFSS and NHANES input was re-read from a shared harmonised dataset, and every analysis was rerun under unchanged code settings, seeds, roles, lock sets, graphs, readings and decision rules. NHIS is not in that dataset and is unchanged. The reasons, the time of the decision and the results seen before it are recorded in `../eswa2026/preregistration/public_copies/deviation_p5_reanalysis_en_v1_20261118_1710.md`.

- The subfolders mirror `../q1/`. They differ from it only in the output folder, in the SHA-256 of the analytic tables and in the reference values of reproduction checks, which now point to the rerun on the shared dataset.
- `v10_tables/p7_from_p5.py` builds the analysis frames from the shared dataset. It applies the inclusion rules of this study (age at least 20, examined, not pregnant, label present, complete cases) and the feature coding of this study.
- `v10_tables/` also holds the scripts that collect the reported numbers (`collect_v10.py`), compare them with the first analysis (`numbers_v9_v10.py`), and write the rows of each supplementary table (`*_rows.py`).

Paths in the scripts point to the authors' machine. Survey data, fitted models and guideline documents are not included. Derived summary results of this rerun are in `../eswa2026/results_v10/`.
