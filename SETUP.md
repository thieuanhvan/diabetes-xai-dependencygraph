# Setup

## Get the code

```bash
git clone https://github.com/thieuanhvan/diabetes-xai-dependencygraph.git
cd diabetes-xai-dependencygraph
```

## Point the runners at the published pipeline

The runners import the published pipeline (`diabetes-xai-counterfactual`,
tag `v1.0-ijmi`). Provide it either way:

```bash
# Option A: clone it as a sibling folder (the default the runners look for)
#   parent/
#     diabetes-xai-dependencygraph/               <- this repo
#     diabetes-xai-counterfactual/   <- at tag v1.0-ijmi
git clone https://github.com/thieuanhvan/diabetes-xai-counterfactual.git ../diabetes-xai-counterfactual
( cd ../diabetes-xai-counterfactual && git checkout v1.0-ijmi )

# Option B: set an environment variable
export PIPELINE_REPO=/path/to/diabetes-xai-counterfactual
```

Verified: with the pipeline at `v1.0-ijmi`, `run_audit_dump.py` reproduces test
AUC 0.8234 and 1523 total counterfactual changes.

## Never modify the pipeline

The runners import it read-only and patch the taxonomy in memory. Paper 4 is
already tagged `v1.0-ijmi`; nothing here writes into it.
