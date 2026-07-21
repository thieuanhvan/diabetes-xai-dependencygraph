"""Multi-seed sweep (paper Section VI robustness check).

Runs BOTH configurations across the five seeds used by the audited paper's own
multi-seed ablation: {42, 123, 2024, 7, 31337}. The seed varies XGBoost
training, the train/test split, and DiCE sampling.

  Config A  published per-query taxonomy
  Config B  A + indicators (GenHlth, PhysHlth, MentHlth) reclassified as
            non-levers, hence excluded from features_to_vary

Question: is the validity gain of Config B real, or seed noise?
The audited paper reports CV = 0.72% on validity across these five seeds.

The audit rule now comes from depgraph.audit, which implements the rule as Section
IV-E states it (a lever with an EDGE into the indicator being moved) alongside
the weaker role-only rule this script used previously. Both are reported so the
marginal contribution of the edge set is visible rather than assumed.

Every counterfactual's feature-level changes are also written out per seed and
per config, so any later change to the edge set or the tier assignment can be
re-audited with analysis/audit_rules.py without regenerating counterfactuals.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

import os
# Locate the published pipeline (diabetes-xai-counterfactual @ tag v1.0-ijmi).
# Set PIPELINE_REPO, or place that repo as a sibling of this one.
REPO = Path(os.environ.get(
    "PIPELINE_REPO",
    Path(__file__).parent.parent / "diabetes-xai-counterfactual",
)).resolve()
sys.path.insert(0, str(REPO))
P7SRC = Path(__file__).parent / "src"   # this repo's own module
sys.path.insert(0, str(P7SRC))

from src.pipelines.counterfactual import feature_taxonomy as FT
from src.pipelines.counterfactual.actionability import actionability_score
from src.pipelines.counterfactual.dice_runner import DiCEConfig, DiCERunner
from src.pipelines.counterfactual.feature_taxonomy import get_discrete_features
from src.pipelines.data.loader import TARGET_COL, load_dataset
from src.pipelines.evaluate.cf_metrics import validity
from src.pipelines.models.xgb_train import XGBConfig, train_xgb
from src.pipelines.preprocessing.pipeline import get_train_test_split
from src.utils.seed import seed_everything

from depgraph.audit import summarise            # the rule of Section IV-E
from depgraph.runlog import RunLog
from depgraph.nodes import TIER

SEEDS = [42, 123, 2024, 7, 31337]
# Excluded from features_to_vary by Config B. DiffWalk is in the indicator tier
# too, but the audited generator never varies it, so removing it is a no-op.
INDICATORS = ["GenHlth", "PhysHlth", "MentHlth"]

RUNLOG = RunLog("run_seed_sweep")

cfg = yaml.safe_load(open(REPO / "configs" / "default.yaml"))
with RUNLOG.step("load BRFSS 2021"):
    X, y = load_dataset(REPO / cfg["paths"]["data_csv"])
discrete = set(get_discrete_features())

# Snapshot the pristine taxonomy so Config A is never contaminated by Config B.
PRISTINE = dict(FT.FEATURE_TAXONOMY)


def one(seed: int, graph: bool) -> dict:
    FT.FEATURE_TAXONOMY.clear()
    FT.FEATURE_TAXONOMY.update(PRISTINE)
    if graph:
        for f in INDICATORS:
            s = PRISTINE[f]
            FT.FEATURE_TAXONOMY[f] = FT.FeatureSpec(
                s.name, FT.Mutability.CONDITIONAL, s.value_range, s.semantic_label
            )

    seed_everything(seed)
    Xtr, Xte, ytr, yte = get_train_test_split(
        X, y, test_size=cfg["split"]["test_size"], seed=seed, stratify=cfg["split"]["stratify"]
    )
    xgb_cfg = dict(cfg["xgboost"]); xgb_cfg["random_state"] = seed
    res = train_xgb(Xtr, ytr, Xte, yte, XGBConfig(**xgb_cfg))
    n_eval = min(cfg["evaluate"]["n_test_instances"], len(Xte))
    queries = Xte.iloc[np.argsort(res["proba"])[-n_eval:]].reset_index(drop=True)

    seed_everything(seed)
    runner = DiCERunner(
        model=res["model"], X_train=Xtr, y_train=ytr, target_col=TARGET_COL,
        config=DiCEConfig(
            method=cfg["dice"]["method"], n_counterfactuals=cfg["dice"]["n_counterfactuals"],
            desired_class=cfg["dice"]["desired_class"],
            proximity_weight=cfg["dice"]["proximity_weight"],
            diversity_weight=cfg["dice"]["diversity_weight"], per_query=True,
        ),
    )
    cfe = runner.generate(queries)

    vals, acts = [], []
    per_cf = []            # one entry per CF: the set of features it changes
    chg_rows = []          # long-form dump, so the audit can be redone offline
    n_chg = n_ind = n_cf = n_nocf = 0
    for i in range(len(queries)):
        q = queries.iloc[i]; obj = cfe[i]
        cfs = obj.final_cfs_df if obj is not None else None
        if cfs is None or len(cfs) == 0:
            n_nocf += 1
            continue
        d = cfs.drop(columns=[TARGET_COL]) if TARGET_COL in cfs.columns else cfs
        d = d.copy()
        for c in discrete:
            if c in d.columns:
                d[c] = d[c].round().astype(int)
        preds = res["model"].predict(d.values)
        vals.append(validity(preds, cfg["dice"]["desired_class"]))
        acts.append(float(np.mean([actionability_score(q, d.iloc[j])["score"] for j in range(len(d))])))
        for k in range(len(d)):
            n_cf += 1
            chg = []
            for f in queries.columns:
                b, a = float(q[f]), float(d[f].iloc[k])
                if (int(round(b)) != int(round(a))) if f in discrete else abs(b - a) > 1e-6:
                    chg.append(f)
                    chg_rows.append({"query_i": i, "cf_k": k, "feature": f,
                                     "x_before": b, "x_after": a, "delta": a - b})
            n_chg += len(chg)
            n_ind += sum(1 for f in chg if TIER.get(f) == "indicator")
            per_cf.append(chg)

    tag = "graph" if graph else "published"
    out = REPO / "outputs_kg"
    out.mkdir(exist_ok=True)
    pd.DataFrame(chg_rows).to_csv(out / f"sweep_changes_seed{seed}_{tag}.csv", index=False)

    row = {
        "seed": seed, "config": tag,
        "auc": round(float(res["auc"]), 4),
        "validity": round(float(np.mean(vals)), 4),
        "actionability": round(float(np.mean(acts)), 4),
        "total_changes": n_chg, "indicator_changes": n_ind,
        "queries_no_cf": n_nocf,
    }
    # Both rules, both readings. "narrow/role" reproduces what this script
    # reported before; "narrow/edge" is the rule Section IV-E defines.
    for reading in ("narrow", "broad"):
        for rule in ("role", "edge"):
            summ = summarise(per_cf, reading=reading, rule=rule)
            pre = f"{reading}_{rule}"
            row[f"{pre}_cf_touching"] = summ["cf_touching_target"]
            row[f"{pre}_unsupported_cfs"] = summ["cf_unsupported"]
            row[f"{pre}_unsupported_changes"] = summ["unsupported_changes"]
    row["pure_indicator_cfs"] = summarise(per_cf)["cf_fully_unactionable"]
    # Backwards-compatible aliases for the columns the paper currently cites.
    row["unsupported_cfs"] = row["narrow_role_unsupported_cfs"]
    return row


rows = []
for s in SEEDS:
    for graph in (False, True):
        with RUNLOG.step(f"seed {s} / {'graph' if graph else 'published'}"):
            r = one(s, graph)
        rows.append(r)
        print(f"seed={s:6d} {r['config']:10s} AUC={r['auc']:.4f} "
              f"validity={r['validity']:.4f} ind={r['indicator_changes']:4d} "
              f"unsup(role)={r['narrow_role_unsupported_cfs']:4d} "
              f"unsup(edge)={r['narrow_edge_unsupported_cfs']:4d} "
              f"pure={r['pure_indicator_cfs']:4d}", flush=True)
        pd.DataFrame(rows).to_csv(REPO / "outputs_kg" / "seed_sweep.csv", index=False)

df = pd.DataFrame(rows)
print("\n" + "=" * 70)
piv = df.pivot(index="seed", columns="config", values="validity")
piv["delta"] = piv["graph"] - piv["published"]
print(piv.to_string())
print("=" * 70)
pub, gr = df[df.config == "published"]["validity"], df[df.config == "graph"]["validity"]
d = piv["delta"]
print(f"\npublished validity : mean={pub.mean():.4f}  sd={pub.std():.4f}  CV={pub.std()/pub.mean()*100:.2f}%")
print(f"graph     validity : mean={gr.mean():.4f}  sd={gr.std():.4f}  CV={gr.std()/gr.mean()*100:.2f}%")
print(f"\nΔ validity         : mean={d.mean():+.4f}  sd={d.std():.4f}  "
      f"min={d.min():+.4f}  max={d.max():+.4f}")
print(f"Δ positive in {(d > 0).sum()}/{len(d)} seeds")
from scipy import stats
t, p = stats.ttest_rel(gr.values, pub.values)
print(f"paired t-test      : t={t:.3f}  p={p:.4f}   "
      f"(n={len(d)} computational replicates, reported descriptively)")

print("\n" + "=" * 70)
print("AUDIT RULE COMPARISON, published config, per seed")
print("=" * 70)
pubrows = df[df.config == "published"]
print(pubrows[["seed", "narrow_role_unsupported_cfs", "narrow_edge_unsupported_cfs",
               "broad_role_unsupported_cfs", "broad_edge_unsupported_cfs",
               "pure_indicator_cfs", "indicator_changes"]].to_string(index=False))
extra = pubrows["narrow_edge_unsupported_cfs"] - pubrows["narrow_role_unsupported_cfs"]
print(f"\ncounterfactuals caught ONLY by the edge rule: "
      f"mean={extra.mean():.1f}  min={extra.min()}  max={extra.max()}")
print("If this is 0 across all seeds, the edge set adds nothing the role tier")
print("does not already give, and the paper must say so.")

RUNLOG.finish(REPO / "outputs_kg")
