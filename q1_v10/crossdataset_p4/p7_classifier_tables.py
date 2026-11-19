"""Classifier robustness tables (Logistic Regression, Random Forest, XGBoost) for the P7 journal version.

Reads the per-counterfactual result files and computes, per classifier and survey, the same quantities as
main Tables 3 and 7: published-mode validity and audit shares (per patient, averaged over seeds and that
patient's counterfactuals), and paired patient-bootstrap contrasts for the indicator lock and route-aware
enforcement (2,000 resamples, 95% percentile intervals, same RNG seeds as the locked bootstraps).

XGBoost reference: locked tags (_v2 NHIS, _v3 NHANES, _exh) plus _xgbrand for BRFSS 2021 DiCE random,
rerun through the same runner so that the BRFSS contrasts are paired as for the other classifiers.
Writes classifier_robustness_random.csv and classifier_robustness_exh.csv next to the results folder.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
from depgraph.audit import classify  # noqa: E402

R = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4") / "results"
B = 2000
DS = ["brfss2021", "nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c",
      "nhanes2021-2023_diag", "nhanes2021-2023_a1c"]
XGB_RANDOM = {"brfss2021": "_xgbrand", "nhis2022": "_v2", "nhis2024": "_v2"}


def tag(clf, ds, gen):
    if gen == "exh":
        return "_exh" if clf == "xgb" else f"_{clf}_exh"
    if clf == "xgb":
        return XGB_RANDOM.get(ds, "_v3")
    return f"_{clf}"


def classified(df):
    sets = [set(str(s).split(";")) - {"", "nan"} for s in df.changed.fillna("")]
    cl = [classify(s, reading="narrow", rule="edge") for s in sets]
    return df.assign(touch=[r["touches_target"] for r in cl], unsup=[r["unsupported"] for r in cl],
                     fully=[r["fully_unactionable"] for r in cl])


def ci(x, idx):
    bs = np.array([np.nanmean(x[i]) for i in idx])
    return np.nanmean(x), np.quantile(bs, .025), np.quantile(bs, .975)


def random_rows():
    rows = []
    for clf in ["xgb", "lr", "rf"]:
        for ds in DS:
            t = tag(clf, ds, "random")
            fc, fs = R / f"cross_{ds}{t}_changes.csv", R / f"cross_{ds}{t}_summary.csv"
            if not fc.exists():
                continue
            s, ch = pd.read_csv(fs), pd.read_csv(fc)
            for suf in "bc":  # seeds run in parallel processes (Random Forest, BRFSS: b = 31337, c = 7)
                extra = R / f"cross_{ds}{t}{suf}_summary.csv"
                if extra.exists():
                    s2 = pd.read_csv(extra)
                    s = pd.concat([s[~s.seed.isin(s2.seed)], s2], ignore_index=True)
                    c2 = pd.read_csv(R / f"cross_{ds}{t}{suf}_changes.csv")
                    ch = pd.concat([ch[~ch.seed.isin(c2.seed)], c2], ignore_index=True)
            if not {"published", "tableV", "route_A"} <= set(s["mode"]) or len(s) < 15:
                print("incomplete", clf, ds, len(s))
                continue
            df = classified(ch)
            pp = df.groupby(["mode", "pid"])[["valid", "touch", "unsup", "fully"]].mean()
            cohort = int(s.cohort.iloc[0])
            pats = np.arange(cohort)
            rng = np.random.default_rng(20261015)
            idx = [rng.choice(cohort, cohort, replace=True) for _ in range(B)]
            pub = pp.loc["published"].reindex(pats)
            row = {"clf": clf, "dataset": ds, "auc": float(s.auc.iloc[0]), "cohort": cohort}
            for m in ["valid", "touch", "unsup", "fully"]:
                row[f"pub_{m}"] = np.nanmean(pub[m].to_numpy())
            for mode in ["tableV", "route_A"]:
                mm = pp.loc[mode].reindex(pats) if mode in pp.index.get_level_values(0) else pub * np.nan
                d = (mm["valid"] - pub["valid"]).to_numpy()
                e, lo, hi = ci(d, idx)
                row.update({f"d_{mode}": e, f"d_{mode}_lo": lo, f"d_{mode}_hi": hi,
                            f"n_pairs_{mode}": int(np.sum(~np.isnan(d))),
                            f"lvl_{mode}_valid": np.nanmean(mm["valid"].to_numpy()),
                            f"lvl_{mode}_unsup": np.nanmean(mm["unsup"].to_numpy()),
                            f"empty_cells_{mode}": int(s[s["mode"] == mode].queries_with_no_cf.sum())})
            rows.append(row)
    return pd.DataFrame(rows)


def exh_rows():
    rows = []
    for clf in ["xgb", "lr", "rf"]:
        for ds in DS:
            t = tag(clf, ds, "exh")
            fc, fs = R / f"cross_{ds}{t}_changes.csv", R / f"cross_{ds}{t}_summary.csv"
            if not fc.exists():
                continue
            s = pd.read_csv(fs).set_index("mode")
            if len(s) < 3:
                print("incomplete", clf, ds, "exh")
                continue
            df = classified(pd.read_csv(fc))
            share = df.groupby(["mode", "pid"])[["touch", "unsup", "fully"]].mean()
            best = df.sort_values(["n_changes", "dist"]).groupby(["mode", "pid"]).first()[["n_changes", "dist"]]
            pp = share.join(best)
            cohort = int(s.cohort.iloc[0])
            pats = np.arange(cohort)
            rng = np.random.default_rng(20261018)
            idx = [rng.choice(cohort, cohort, replace=True) for _ in range(B)]
            pub = pp.loc["published"].reindex(pats)
            row = {"clf": clf, "dataset": ds, "auc": float(s.auc.iloc[0]), "cohort": cohort}
            for m in ["touch", "unsup", "fully", "n_changes", "dist"]:
                row[f"pub_{m}"] = np.nanmean(pub[m].to_numpy())
            for mode in ["tableV", "route_A"]:
                mm = pp.loc[mode].reindex(pats)
                d = (mm["dist"] - pub["dist"]).to_numpy()
                e, lo, hi = ci(d, idx)
                row.update({f"d_dist_{mode}": e, f"d_dist_{mode}_lo": lo, f"d_dist_{mode}_hi": hi,
                            f"no_cf_{mode}": int(s.loc[mode, "queries_with_no_cf"])})
            rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    a, b = random_rows(), exh_rows()
    a.to_csv(R.parent / "classifier_robustness_random.csv", index=False)
    b.to_csv(R.parent / "classifier_robustness_exh.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(a.round(4).to_string(index=False))
    print(b.round(4).to_string(index=False))
