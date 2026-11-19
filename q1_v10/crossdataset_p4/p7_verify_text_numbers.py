"""Pre-submission check: recompute numbers quoted in the running text of P7 (and S5, S10, supplementary prose)
from the locked result files. Prints source values (truncated as reported) for comparison with the text."""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
import depgraph.nodes as N  # noqa: E402
from depgraph.audit import classify  # noqa: E402

C = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4")
R = C / "results"
REPO = Path("C:/Repos/uit/diabetes-xai-dependencygraph/outputs")
NH = ["nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c", "nhanes2021-2023_diag", "nhanes2021-2023_a1c"]
ALL = ["brfss2021"] + NH
rt = lambda ds: "_v2" if ds.startswith("nhis") else "_v3"  # noqa: E731


def tr(x, k):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


def p(x):
    return f"{tr(x * 100, 2):.2f}"


def f4(x):
    return f"{tr(x, 4):.4f}"


def rng(vals, fmt=p):
    v = list(vals)
    return f"{fmt(min(v))}–{fmt(max(v))}"


def sets(df):
    return [set(str(s).split(";")) - {"", "nan"} for s in df.changed.fillna("")]


def classified(f):
    df = pd.read_csv(f)
    cl = [classify(s, reading="narrow", rule="edge") for s in sets(df)]
    return df.assign(touch=[r["touches_target"] for r in cl], unsup=[r["unsupported"] for r in cl],
                     fully=[r["fully_unactionable"] for r in cl], sset=sets(df))


def head(t):
    print(f"\n== {t}")


# ---------- intro / S10: conference seed sweep
ss = pd.read_csv(REPO / "seed_sweep.csv")
head("Intro/S10 conference seed sweep (mean over seeds)")
for cfg in ss.config.unique():
    x = ss[ss.config == cfg]
    print(cfg, "validity", f4(x.validity.mean()), "actionability", f4(x.actionability.mean()), "seeds", len(x))
ec = pd.read_csv(REPO / "enforcement_comparison.csv")
print("enforcement_comparison cols:", list(ec.columns)[:12])
print(ec.head(8).to_string())
re_ = pd.read_csv(REPO / "route_enforcement.csv")
b = re_[re_.label == "baseline_published"]
print("this-article BRFSS published validity", f4(b.validity.mean()), "actionability_eq1", f4(b.actionability_eq1.mean()))
mr = pd.read_csv(REPO / "model_reproducibility.csv")
print("cohort cutoff (200th score)", mr.cohort_cutoff.tolist())

# ---------- random: rounds, NHIS falls
head("DiCE random route-aware rounds (mean over seeds), NHIS+NHANES")
rr = []
for ds in NH:
    s = pd.read_csv(R / f"cross_{ds}{rt(ds)}_summary.csv")
    v = s[s["mode"] == "route_A"].rounds_mean.mean(); rr.append(v); print(ds, f4(v), "max rounds_mean", s.rounds_mean.max())
print("range", rng(rr, f4))
bt = pd.concat([pd.read_csv(C / "cross_dataset_bootstrap.csv").query("dataset.str.startswith('nhis')", engine="python"),
                pd.read_csv(C / "cross_dataset_bootstrap_v3.csv")])
x = bt[(bt.contrast == "minus_published")]
print("NHIS contrasts (abs):", [(r.dataset, r["mode"], f4(r.est)) for _, r in x[x.dataset.str.startswith("nhis")].iterrows()])
print("NHANES route-aware CIs:", [(r.dataset, f4(r.ci_lo), f4(r.ci_hi)) for _, r in x[(x["mode"] == "route_A") & x.dataset.str.startswith("nhanes")].iterrows()])

# ---------- S11 ranges
head("S11 random share of requested published / route")
cy = pd.read_csv(C / "cross_coverage_yield_random_final.csv")
for m in ["published", "tableV", "route_A"]:
    print(m, rng(cy[cy["mode"] == m].yield_per_5, lambda v: f"{tr(v, 4):.4f}"))
print("lock/route share vs validity level (random):")
for _, r in bt[(bt.contrast == "level") & (bt.metric == "valid") & (bt["mode"] != "published")].iterrows():
    y = cy[(cy.config == r.dataset) & (cy["mode"] == r["mode"])].yield_per_5.iloc[0]
    print(" ", r.dataset, r["mode"], "share", f4(y), "per-patient validity level", f4(r.est))
gy = pd.read_csv(C / "cross_coverage_yield_gen2.csv")
emp = 1 - gy[gy["mode"] == "route_A"].cell_coverage
print("genetic route empty cells:", [(c, p(e)) for c, e in zip(gy[gy["mode"] == "route_A"].config, emp)])
print("genetic empty cells in other modes max:", p((1 - gy[gy["mode"] != "route_A"].cell_coverage).max()))
for ds in ALL:
    for t in (rt(ds) if ds != "brfss2021" else None, "_gen2"):
        if t is None:
            continue
        d = pd.read_csv(R / f"cross_{ds}{t}_changes.csv"); s = pd.read_csv(R / f"cross_{ds}{t}_summary.csv")
        coh = int(s.cohort.iloc[0])
        for m in ["published", "tableV", "route_A"]:
            k = d[d["mode"] == m].pid.nunique()
            if k < coh:
                print(f"  {ds}{t} {m}: patients with no CF in any seed = {coh - k} of {coh}")
print("(random/genetic lines above list every patient-level gap)")

# ---------- exhaustive
head("Exhaustive")
be = pd.read_csv(C / "cross_dataset_bootstrap_exh.csv")
main = be[be.dataset.isin(ALL)]
nc = main[(main.contrast == "minus_published") & (main.metric == "n_changes")]
print("max Δ n_changes", f4(nc.est.max()), "min", f4(nc.est.min()))
dd = main[(main.contrast == "minus_published") & (main.metric == "dist")]
print("Δ dist range", rng(dd.est, f4), "min ci_lo", f4(dd.ci_lo.min()))
for ds in ALL:
    s = pd.read_csv(R / f"cross_{ds}_exh_summary.csv")
    print(ds, "max secs", s.secs.max(), "coverage min", s.coverage.min())
mh = be[be.dataset.str.endswith("_mh") & (be.contrast == "minus_published") & (be.metric == "dist") & (be["mode"] == "route_A")]
print("observed-code route Δ dist", rng(mh.est, f4), "min ci_lo", f4(mh.ci_lo.min()))
dt, du, dn = [], [], []
for ds in NH:
    a = be[(be.dataset == ds) & (be.contrast == "level") & (be["mode"] == "published")].set_index("metric").est
    c = be[(be.dataset == ds + "_mh") & (be.contrast == "level") & (be["mode"] == "published")].set_index("metric").est
    dt.append(abs(a.touch - c.touch)); du.append(abs(a.unsup - c.unsup)); dn.append(abs(a.n_changes - c.n_changes))
    for met in ["touch", "unsup", "fully"]:
        print(f"  S5b {ds} obs-codes {met} {p(c[met])}")
    cc = be[(be.dataset == ds + "_mh") & (be.contrast == "minus_published") & (be.metric == "dist") & (be["mode"] == "route_A")].iloc[0]
    print(f"  S5b {ds} obs-codes route Δdist +{f4(cc.est)} [{f4(cc.ci_lo)}, {f4(cc.ci_hi)}]")
print("max |Δtouch|", p(max(dt)), "max |Δunsup|", p(max(du)), "max |Δn_changes| best", f4(max(dn)))

# ---------- S5 part 1 from per-CF files (independent of cross_menthlth_sensitivity.csv)
head("S5 part 1 (pooled over CFs, published mode, six NHIS/NHANES configs)")
IND = {"GenHlth", "PhysHlth", "MentHlth"}
sens = {}
for gen, tag in (("DiCE random", None), ("DiCE genetic", "_gen2"), ("Exhaustive search", "_exh")):
    rows = []
    for ds in NH:
        d = pd.read_csv(R / f"cross_{ds}{tag or rt(ds)}_changes.csv")
        d = d[d["mode"] == "published"]; S = sets(d)
        mh = np.mean(["MentHlth" in s for s in S]); ti = np.mean([bool(s & IND) for s in S])
        tg = np.mean([bool(s & {"GenHlth", "PhysHlth"}) for s in S]); only = np.mean([(s & IND) == {"MentHlth"} for s in S])
        rows.append((mh, ti, tg, only, ti - tg))
    a = np.array(rows); sens[gen] = a
    print(gen, "| MentHlth", rng(a[:, 0]), "| touch", rng(a[:, 1]), "| GenHlth", rng(a[:, 2]), "| only MentHlth", rng(a[:, 3]))
allv = np.vstack(list(sens.values()))
print("GenHlth across generators", rng(allv[:, 2]), "| drop (touch−GenHlth) range", rng(allv[:, 4]))
cms = pd.read_csv(C / "cross_menthlth_sensitivity.csv")
print("stored cross_menthlth_sensitivity.csv cols", list(cms.columns))

# ---------- mechanism / BMI recoding
head("BMI recoding cohorts/AUC")
for ds in ["nhanes2017-2020_diag_bmi4", "nhanes2017-2020_a1c_bmi4"]:
    for t in ["_bmi4rand", "_exh"]:
        s = pd.read_csv(R / f"cross_{ds}{t}_summary.csv")
        print(ds, t, "cohort", s.cohort.unique(), "auc", s.auc.unique())
bb = pd.read_csv(C / "cross_dataset_bootstrap_bmi4rand.csv")
for _, r in bb[bb.contrast == "minus_published"].iterrows():
    print(" ", r.dataset, r["mode"], f"{f4(r.est)} [{f4(r.ci_lo)}, {f4(r.ci_hi)}]")
for _, r in be[be.dataset.str.contains("bmi4") & (be.contrast == "minus_published")].iterrows():
    print(" ", r.dataset, r["mode"], r.metric, f"{f4(r.est)} [{f4(r.ci_lo)}, {f4(r.ci_hi)}]")
for _, r in bt[(bt.contrast == "minus_published") & bt.dataset.str.startswith("nhanes2017")].iterrows():
    print("  integer BMI", r.dataset, r["mode"], f"{f4(r.est)} [{f4(r.ci_lo)}, {f4(r.ci_hi)}]")
for _, r in be[be.dataset.str.startswith("nhanes2017-2020_") & ~be.dataset.str.contains("_") .__invert__()].iterrows():
    pass
ib = be[be.dataset.isin(["nhanes2017-2020_diag", "nhanes2017-2020_a1c"]) & (be.contrast == "minus_published") & (be["mode"] == "route_A")]
for _, r in ib.iterrows():
    print("  integer BMI exh", r.dataset, r.metric, f"{f4(r.est)} [{f4(r.ci_lo)}, {f4(r.ci_hi)}]")

# ---------- limitations: BMI treatable, Smoker
head("BMI as treatable (pooled over CFs, published mode)")
orig = N.TIER["BMI"]
files = {"brfss gen2": "cross_brfss2021_gen2_changes.csv", **{ds: f"cross_{ds}{rt(ds)}_changes.csv" for ds in NH}}
u0s, u1s = [], []
for k, f in files.items():
    d = pd.read_csv(R / f); d = d[d["mode"] == "published"]; S = sets(d)
    N.TIER["BMI"] = orig; u0 = np.mean([classify(s, reading="narrow", rule="edge")["unsupported"] for s in S])
    N.TIER["BMI"] = "treatable"; u1 = np.mean([classify(s, reading="narrow", rule="edge")["unsupported"] for s in S])
    N.TIER["BMI"] = orig
    print(k, p(u0), "->", p(u1))
    if k != "brfss gen2":
        u0s.append(u0); u1s.append(u1)
print("NHIS/NHANES random", rng(u0s), "->", rng(u1s))

head("Smoker")
for gen, tf in (("random", lambda ds: rt(ds)), ("genetic", lambda ds: "_gen2")):
    v = []
    for ds in ALL:
        if gen == "random" and ds == "brfss2021":
            continue
        d = pd.read_csv(R / f"cross_{ds}{tf(ds)}_changes.csv")
        for m in ["published", "tableV", "route_A"]:
            S = sets(d[d["mode"] == m]); v.append((ds, m, np.mean(["Smoker" in s for s in S])))
    print(gen, "range over configs×modes", rng([x[2] for x in v]),
          "| published only", rng([x[2] for x in v if x[1] == "published"]))
ev = []
for ds in ALL:
    d = pd.read_csv(R / f"cross_{ds}_exh_changes.csv")
    ev.append(d)
e = pd.concat(ev); S = sets(e)
print("exhaustive pooled all configs/modes Smoker", p(np.mean(["Smoker" in s for s in S])),
      "| published only", p(np.mean(["Smoker" in s for s in sets(e[e["mode"] == "published"])])))
nos = {}
for ds in ["brfss2021"] + NH:
    f = R / f"cross_{ds}_nosmk_exh_summary.csv"
    print(ds, "nosmk_exh exists", f.exists())
for _, r in be[be.dataset.str.endswith("_nosmk") & (be.contrast == "minus_published")].iterrows():
    base = be[(be.dataset == r.dataset[:-6]) & (be.contrast == "minus_published") & (be["mode"] == r["mode"]) & (be.metric == r.metric)].est.iloc[0]
    if abs(base - r.est) > 1e-12:
        print("  nosmk differs:", r.dataset, r["mode"], r.metric, f4(base), f4(r.est))
print("(no 'nosmk differs' lines = identical costs)")
