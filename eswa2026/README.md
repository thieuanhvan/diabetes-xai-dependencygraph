# Artefacts for the journal extension (three surveys, three diseases, six generators)

This folder holds the data and records behind the journal extension of the FAIR 2026 paper. That extension audits counterfactual recourse for diabetes, chronic kidney disease (CKD) and hypertension with a guideline dependency graph stored as a knowledge graph. The analysis code is in `../q1/`, and the graph library is in `../src/depgraph/`.

| Folder | Contents |
|---|---|
| `kg/` | Dependency graphs in RDF Turtle (diabetes, CKD); node and role tables with terminology codes; the triple table with the provenance of every route; KDIGO extraction passages (quotation and page) from both extractors; agreement statistics |
| `sparql/` | SPARQL audit queries and the recorded checks of SPARQL against the Python audit |
| `preregistration/public_copies/` | The internally time-stamped protocol, the hypertension addendum (three hashed versions), the post-hoc plans (B-P1, S-P1 to S-P3, S-P4, S-P5, S-P6) and the deviation log |
| `preregistration/reviewer_copies/` | The anonymised copies given to reviewers |
| `preregistration/SHA256_originals_and_public_copies.txt` | The SHA-256 of each original file and of its public copy |
| `results/` | Derived summary results: analysis JSON and CSV files and per-run summaries. Survey rows and per-counterfactual change files are not included; the code in `../q1/` regenerates them from the public CDC files. |

## Checking the hashes

Each plan was frozen by its SHA-256 hash before it ran. Three public copies are byte-identical to their originals, so their hashes can be checked directly: S-P1 to S-P3, S-P6 and the deviation log. In the other seven files, local file-system paths were replaced by `<local>`, and nothing else was changed. For these, the hash of the original is listed in the first column, and the original files are available to editors and reviewers on request.

## Data

Survey data are not redistributed. They come from the US Centers for Disease Control and Prevention: BRFSS 2021, NHIS 2022 and 2024, NHANES 2017–March 2020 and August 2021–August 2023. Guideline documents and fitted models are not included either.
