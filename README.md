# diabetes-xai-kg

A guideline-sourced dependency graph for auditing counterfactual recourse in
diabetes risk prediction. Companion code for the FAIR 2026 paper *"Levers and
Indicators."*

**Status: private until FAIR notification (15 September 2026).**

## What this is

The published pipeline `diabetes-xai-counterfactual` constrains counterfactuals
with a flat, per-feature intervention-direction taxonomy. This repository recasts
that knowledge layer as a directed dependency graph K_G, in which a feature's
direction is a node attribute and an intervention route is an edge, every edge
sourced from a numbered ADA Standards of Care recommendation with its evidence
grade. It then audits the published counterfactuals against K_G and shows that
11% of them recommend nothing the patient can act on, undetected by the
direction-only actionability metric.

## Relationship to the published pipeline

This repo contains only Paper 7's own code. It reuses, read-only, the published
pipeline `diabetes-xai-counterfactual` (tag `v1.0-ijmi`), which is a **separate**
repository and is never modified. The runners import its modules and patch the
taxonomy at run time, in memory. See SETUP.md for how to point at it.

## Layout

```
src/kg/            the knowledge graph
    nodes.py       21 features: direction class + role tier (lever/treatable/indicator/immutable)
    edges.py       26 dependency edges, each with an ADA recommendation and evidence grade
run_audit_dump.py  reproduce the published run, dump raw per-CF changes
run_enforce.py     re-run with indicators excluded from features_to_vary; measure the cost
run_seed_sweep.py  both configurations across the audited paper's five seeds
analysis/
    make_figures.py  Figure 1 (the graph) from src/kg/
    figures/         generated figures
outputs/           result CSVs
manuscript/        paper7.tex, paper7.pdf, fig1.pdf (IEEEtran, FAIR 2026)
configs/           note on reused pipeline config
```

## Reproduce

```bash
pip install -r requirements.txt
# point at the published pipeline (see SETUP.md), then:
python run_audit_dump.py     # ~4 min   reproduces AUC 0.8234, 1523 CF changes
python run_enforce.py        # ~8 min
python run_seed_sweep.py     # ~35 min
python analysis/make_figures.py
```

## Headline results

Audit (stable across five seeds): 291-350 counterfactual changes target
health-status indicators; 96-111 of 1000 counterfactuals recommend nothing
actionable; all scored at violation rate 0.000 by the direction-only metric.

Enforcement (indicators excluded): validity improves in 5 of 5 seeds
(0.8012 -> 0.8266 mean; paired t = 2.90, p = 0.044) at no cost; the
direction-only actionability score barely moves (0.9804 -> 0.9742), being
structurally unable to see the difference.

## Citation

See CITATION.cff. The published pipeline is Thieu, *Int. J. Med. Inform.* 219
(2026) 106555, doi:10.1016/j.ijmedinf.2026.106555.

## License

MIT (code). ADA guideline text is not reproduced here; edges store only the
recommendation number and grade as bibliographic facts.
