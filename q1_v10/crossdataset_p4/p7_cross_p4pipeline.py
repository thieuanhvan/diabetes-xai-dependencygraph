"""P7 audit + enforcement on NHIS / NHANES through the ORIGINAL P4 pipeline (tag v1.0-ijmi code).

Same objects as the P7 repo runners (run_seed_sweep / run_enforce / run_route_enforce):
  - DiCERunner per-query mode, taxonomy translator, rounding rule and change rule of P4/P7;
  - split get_train_test_split(test 0.2, stratified, seed 42); XGBoost from configs/default.yaml;
  - cohort = 200 highest-risk test patients (no probability threshold, as in P7);
  - modes: published | tableV (GenHlth, PhysHlth, MentHlth patched IMMUTABLE, as run_enforce.py)
           | route_A (rejection + regeneration, seed_everything(seed + 100000 r), MAX_ROUNDS 8,
                      universal reading, lever sources, all ADA edges, as run_route_enforce.py).
Nothing is written into either repository: the taxonomy is patched in memory only.
Dataset adaptations (documented, in memory): value ranges of Income/BMI to the dataset's
coding; NHIS BMI is a 1-4 category, so it is rounded like the discrete features.
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

warnings.filterwarnings("ignore")
P4 = Path("C:/Repos/uit/diabetes-xai-counterfactual")
P7 = Path("C:/Repos/uit/diabetes-xai-dependencygraph")
sys.path.insert(0, str(P4))
sys.path.insert(0, str(P7 / "src"))

from src.pipelines.counterfactual import feature_taxonomy as FT  # noqa: E402
from src.pipelines.counterfactual.feature_taxonomy import FeatureSpec, Mutability  # noqa: E402
from src.pipelines.counterfactual.dice_runner import DiCEConfig, DiCERunner  # noqa: E402
from src.pipelines.evaluate.cf_metrics import validity  # noqa: E402
from src.pipelines.models.xgb_train import XGBConfig, train_xgb  # noqa: E402
from src.pipelines.preprocessing.pipeline import get_train_test_split  # noqa: E402
from src.utils.seed import seed_everything  # noqa: E402
from depgraph.audit import summarise  # noqa: E402
from depgraph.edges import EDGES  # noqa: E402
from depgraph.nodes import TIER  # noqa: E402

CFG = yaml.safe_load(open(P4 / "configs" / "default.yaml"))
# Machine rule (15/10/2026): below-normal priority and at most 2 worker threads per heavy process.
try:
    import psutil
    import os
    if os.environ.get("P7_LOWPRIO", "1") == "1":
        psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
except Exception:
    pass
# n_jobs stays as in configs/default.yaml (-1): changing it changes the fitted model (found 17/10/2026)
SEEDS = [42, 123, 2024, 7, 31337]
MAX_ROUNDS = 8
N_WANTED = int(CFG["dice"]["n_counterfactuals"])
TABLE_V = ["GenHlth", "PhysHlth", "MentHlth"]
OUT = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4") / "results"
TARGET = "Diabetes_binary"
NHANES_FEATS = ["HighBP", "HighChol", "BMI", "Smoker", "Stroke", "HeartDiseaseorAttack", "PhysActivity",
                "AnyHealthcare", "GenHlth", "MentHlth", "Sex", "Age", "Education", "Income"]


def load(dataset: str):
    """Return X, y with BRFSS/Teboul feature names; patch value ranges to the dataset coding."""
    patches, round_bmi = {}, False
    if dataset.startswith("nhis"):
        year = dataset[4:]
        d = pd.read_csv(f"C:/Repos/uit/nhis-diabetes/outputs/tabular/cdc_nhis_diabetes_{year}.csv").dropna()
        d = d[(d.Age >= 18) & (d.Age < 97)]  # 97-99 are NHIS missing-value codes
        y = d[TARGET].astype(int)
        X = d.drop(columns=[TARGET, "AgeGroup"])
        # NHIS: income 1-5; BMI category 1-4 (2 = healthy). P4's 18.5-35 spans healthy..obese I -> 2..4
        patches = {"Income": (1, 5), "BMI": (2, 4)}
        round_bmi = True
    elif dataset.startswith("nhanes"):
        parts = dataset[6:].split("_")  # e.g. nhanes2017-2020_a1c, or nhanes2017-2020_diag_bmi4
        cyc, lab = parts[0], parts[1]
        bmi4 = len(parts) > 2 and parts[2] == "bmi4"  # P7 journal review 2.8: BMI coded in NHIS's 4 bands
        if lab not in ("diag", "a1c"):
            raise ValueError(f"unknown NHANES label {lab}")
        d = pd.read_csv(f"D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/frames/t4_{cyc}_p5.csv")
        d = d[d.Age >= 20].dropna(subset=NHANES_FEATS + ["Diabetes_self", "HbA1c"])
        y = (d["Diabetes_self"] if lab == "diag" else (d["HbA1c"] >= 6.5)).astype(int)
        X = d[NHANES_FEATS].copy()
        # BRFSS codes BMI as a whole number; NHANES has one decimal. Rounding harmonises the coding
        # and keeps DiCE's post-hoc sparsity search (step = data precision) as cheap as on BRFSS.
        X["BMI"] = X["BMI"].round(0)
        patches = {"Income": (1, 5)}
        if bmi4:
            # NHIS bands: 1 underweight (<18.5), 2 healthy (18.5-24.9), 3 overweight (25-29.9), 4 obese (>=30)
            X["BMI"] = pd.cut(d["BMI"], [-1, 18.5, 25, 30, 1e9], right=False, labels=[1, 2, 3, 4]).astype(int).values
            patches["BMI"] = (2, 4)
            round_bmi = True
    elif dataset == "brfss2021":
        d = pd.read_csv(Path("D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/frames/brfss2021_p5.csv"))
        y = d[TARGET].astype(int)
        X = d.drop(columns=[TARGET])
    else:
        raise ValueError(dataset)
    for f, rng in patches.items():
        s = FT.FEATURE_TAXONOMY[f]
        FT.FEATURE_TAXONOMY[f] = FeatureSpec(f, s.mutability, rng, s.semantic_label + " [range patched]")
    return X.reset_index(drop=True).astype(float), y.reset_index(drop=True), round_bmi


def lever_routes(v):
    return {e.src for e in EDGES if e.dst == v and TIER.get(e.src) == "lever"}


def admissible(chg):
    """Universal reading: every moved indicator needs a pulled lever with an edge into it."""
    S = set(chg)
    return all(S & lever_routes(v) for v in S if TIER.get(v) == "indicator")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--modes", default="published,tableV,route_A")
    ap.add_argument("--seeds", default=",".join(map(str, SEEDS)))
    ap.add_argument("--n", type=int, default=int(CFG["evaluate"]["n_test_instances"]))
    ap.add_argument("--method", default=CFG["dice"]["method"], help="DiCE backend: random | genetic")
    ap.add_argument("--tag", default="", help="suffix for output files, e.g. _v2")
    ap.add_argument("--stop_after", default="", help="YYYY-mm-dd HH:MM; start no new (seed, mode) after this")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    done = OUT / f"cross_{a.dataset}{a.tag}_summary.csv"
    if done.exists() and len(pd.read_csv(done)) >= len(a.seeds.split(",")) * len(a.modes.split(",")):
        print(f"{a.dataset}: already complete, skipped", flush=True)
        return
    seed_everything(CFG["random"]["seed"])
    X, y, round_bmi = load(a.dataset)
    Xtr, Xte, ytr, yte = get_train_test_split(X, y, test_size=CFG["split"]["test_size"],
                                              seed=CFG["random"]["seed"], stratify=CFG["split"]["stratify"])
    res = train_xgb(Xtr, ytr, Xte, yte, XGBConfig(**CFG["xgboost"]))
    model, proba = res["model"], np.asarray(res["proba"])
    from sklearn.metrics import roc_auc_score
    auc = roc_auc_score(yte, proba)
    # Cohort: highest-risk test patients that the model predicts POSITIVE (p >= 0.5), at most n.
    # On BRFSS the 200th score is ~0.69 so this equals P7's top-200; on NHIS/NHANES it prevents
    # queries that are already class 0 (review finding A1). P4 main.py: risk_threshold_min.
    elig = np.where(proba >= 0.5)[0]
    idx = elig[np.argsort(proba[elig])][-min(a.n, len(elig)):]
    queries = Xte.iloc[idx].reset_index(drop=True)
    n_elig = len(elig)
    print(f"{a.dataset}: n={len(X)} prev={y.mean():.3f} test AUC={auc:.4f} cohort={len(queries)} "
          f"eligible(p>=0.5)={n_elig} min p={proba[idx].min():.3f} features={list(X.columns)}", flush=True)
    discrete = (set(FT.get_discrete_features()) | ({"BMI"} if round_bmi else set())) & set(X.columns)

    def changes_of(q, row):
        out = []
        for f in queries.columns:
            b, c = float(q[f]), float(row[f])
            moved = (int(round(b)) != int(round(c))) if f in discrete else abs(b - c) > 1e-6
            if moved:
                out.append(f)
        return out

    def clean(cfs):
        d = cfs.drop(columns=[TARGET]) if TARGET in cfs.columns else cfs.copy()
        for c in discrete:
            if c in d.columns:
                d[c] = d[c].round().astype(int)
        return d[list(X.columns)]

    def runner():
        return DiCERunner(model=model, X_train=Xtr, y_train=ytr, target_col=TARGET,
                          config=DiCEConfig(method=a.method, n_counterfactuals=N_WANTED,
                                            desired_class=CFG["dice"]["desired_class"],
                                            proximity_weight=CFG["dice"]["proximity_weight"],
                                            diversity_weight=CFG["dice"]["diversity_weight"], per_query=True))

    rows, per_cf_rows = [], []
    fs, fc = OUT / f"cross_{a.dataset}{a.tag}_summary.csv", OUT / f"cross_{a.dataset}{a.tag}_changes.csv"
    if fs.exists() and fc.exists():  # resume: keep finished (seed, mode) pairs
        rows = pd.read_csv(fs).to_dict("records")
        per_cf_rows = pd.read_csv(fc).fillna("").to_dict("records")
    finished = {(r["seed"], r["mode"]) for r in rows}
    for seed in [int(s) for s in a.seeds.split(",")]:
        for mode in a.modes.split(","):
            if (seed, mode) in finished:
                continue
            if a.stop_after and pd.Timestamp.now() > pd.Timestamp(a.stop_after):
                print(f"stop_after {a.stop_after} reached; resume later", flush=True)
                return
            t0 = time.time()
            saved = {f: FT.FEATURE_TAXONOMY[f] for f in TABLE_V}
            if mode == "tableV":
                for f, s in saved.items():
                    FT.FEATURE_TAXONOMY[f] = FeatureSpec(f, Mutability.IMMUTABLE, s.value_range, s.semantic_label)
            R = runner()
            per_cf, per_meta, val, rounds, n_no = [], [], [], [], 0
            if mode in ("published", "tableV"):
                seed_everything(seed)
                cfe = R.generate(queries)
                for i in range(len(queries)):
                    obj = cfe[i]
                    cfs = obj.final_cfs_df if obj is not None else None
                    if cfs is None or len(cfs) == 0:
                        n_no += 1
                        continue
                    d = clean(cfs)
                    pr = model.predict(d.values)
                    val.append(validity(pr, CFG["dice"]["desired_class"]))
                    for k in range(len(d)):
                        per_cf.append(changes_of(queries.iloc[i], d.iloc[k]))
                        per_meta.append((i, int(pr[k] == CFG["dice"]["desired_class"])))
                rounds = [1] * len(queries)
            else:
                for i in range(len(queries)):
                    q = queries.iloc[i]
                    kept, kch, r = [], [], 0
                    while len(kept) < N_WANTED and r < MAX_ROUNDS:
                        r += 1
                        seed_everything(seed + 100_000 * r)
                        obj = R.generate(queries.iloc[[i]].reset_index(drop=True))[0]
                        cfs = obj.final_cfs_df if obj is not None else None
                        if cfs is None or len(cfs) == 0:
                            continue
                        d = clean(cfs)
                        for k in range(len(d)):
                            if len(kept) >= N_WANTED:
                                break
                            chg = changes_of(q, d.iloc[k])
                            if admissible(chg):
                                kept.append(d.iloc[k])
                                kch.append(chg)
                    rounds.append(r)
                    if not kept:
                        n_no += 1
                        continue
                    dk = pd.DataFrame(kept)
                    pr = model.predict(dk.values)
                    val.append(validity(pr, CFG["dice"]["desired_class"]))
                    per_cf.extend(kch)
                    per_meta.extend((i, int(v == CFG["dice"]["desired_class"])) for v in pr)
            for f, s in saved.items():
                FT.FEATURE_TAXONOMY[f] = s
            role = summarise(per_cf, reading="narrow", rule="role")
            edge = summarise(per_cf, reading="narrow", rule="edge")
            row = {"dataset": a.dataset, "method": a.method, "mode": mode, "seed": seed, "auc": round(auc, 4), "cohort": len(queries),
                   "eligible": n_elig, "n_cf": len(per_cf),
                   "queries_with_no_cf": n_no, "validity": float(np.mean(val)) if val else np.nan,
                   "n_changes": sum(len(c) for c in per_cf),
                   "indicator_changes": sum(1 for c in per_cf for f in c if TIER.get(f) == "indicator"),
                   "cf_touching_indicator": role["cf_touching_target"],
                   "unsupported_edge_rule": edge["cf_unsupported"],
                   "fully_unactionable": role["cf_fully_unactionable"],
                   "rounds_mean": float(np.mean(rounds)) if rounds else np.nan,
                   "secs": round(time.time() - t0)}
            rows.append(row)
            print(row, flush=True)
            per_cf_rows += [{"dataset": a.dataset, "mode": mode, "seed": seed, "pid": m[0], "valid": m[1],
                             "changed": ";".join(c)} for c, m in zip(per_cf, per_meta)]
            pd.DataFrame(rows).to_csv(OUT / f"cross_{a.dataset}{a.tag}_summary.csv", index=False)
            pd.DataFrame(per_cf_rows).to_csv(OUT / f"cross_{a.dataset}{a.tag}_changes.csv", index=False)


if __name__ == "__main__":
    main()
