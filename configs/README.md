Paper 7 reuses the pipeline configuration of the published repository
(diabetes-xai-counterfactual, tag v1.0-ijmi, configs/default.yaml). The audit
and enforcement runs read that config directly; no separate config is needed
here. The only Paper-7-specific knowledge is declared in code, in src/kg/.
