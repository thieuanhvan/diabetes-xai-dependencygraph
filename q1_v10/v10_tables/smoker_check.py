"""smoker_check.py <crossdataset_p4 folder>: numbers of the Smoker sensitivity paragraph (Supplementary Section S8).
Share of published-mode counterfactuals that change Smoker (exhaustive pooled over configurations; DiCE random range
per configuration) and the enforcement-cost contrasts of the exhaustive search with and without Smoker locked.
Run on the v9 folder first to see which definition reproduces the printed v9 values (0.28%, 1.04-4.19%)."""
import math
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
C = Path(sys.argv[1])
R = C / "results"
DS = ["brfss2021", "nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c", "nhanes2021-2023_diag",
      "nhanes2021-2023_a1c"]
RAND = {"brfss2021": ["_xgbrand", ""], "nhis2022": ["_v2"], "nhis2024": ["_v2"]}


def tr(x, k=2):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


def smk(f):
    d = pd.read_csv(f)
    d = d[d["mode"] == "published"]
    s = d["changed"].fillna("").astype(str).str.split(";").apply(lambda z: "Smoker" in z)
    return int(s.sum()), len(s)


tot = [0, 0]
for ds in DS:
    f = R / f"cross_{ds}_exh_changes.csv"
    if f.exists():
        a, n = smk(f)
        tot[0] += a
        tot[1] += n
        print(f"exh {ds}: {a}/{n} = {tr(100 * a / n):.2f}%")
print(f"exh pooled all: {tot[0]}/{tot[1]} = {tr(100 * tot[0] / tot[1]):.2f}%")
for ds in DS:
    for tag in RAND.get(ds, ["_v3"]):
        f = R / f"cross_{ds}{tag}_changes.csv"
        if f.exists():
            a, n = smk(f)
            print(f"DiCE random {ds}{tag}: {a}/{n} = {tr(100 * a / n):.2f}%")
            break
    f = R / f"cross_{ds}_gen2_changes.csv"
    if f.exists():
        a, n = smk(f)
        print(f"DiCE genetic {ds}: {a}/{n} = {tr(100 * a / n):.2f}%")
b = pd.read_csv(C / "cross_dataset_bootstrap_exh.csv")
b = b[(b.contrast == "minus_published") & (b.metric.isin(["dist", "n_changes"]))]
for ds in DS:
    for mode in ("tableV", "route_A"):
        x = b[(b.dataset == ds) & (b["mode"] == mode)].set_index("metric").est
        y = b[(b.dataset == ds + "_nosmk") & (b["mode"] == mode)].set_index("metric").est
        if len(x) and len(y):
            print(f"cost {ds} {mode}: dist {x['dist']:.6f} vs nosmk {y['dist']:.6f}; n_changes {x['n_changes']:.6f} vs {y['n_changes']:.6f}")
        else:
            print(f"cost {ds} {mode}: missing (main {len(x)}, nosmk {len(y)})")

# Definitions of p7_verify_text_numbers.py (section "Smoker"), which produced the printed paragraph
sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
import depgraph.nodes as N  # noqa: E402
from depgraph.audit import classify  # noqa: E402

NH = DS[1:]
rt = lambda ds: "_v2" if ds.startswith("nhis") else "_v3"  # noqa: E731
sets = lambda d: [set(str(s).split(";")) - {"", "nan"} for s in d.changed.fillna("")]  # noqa: E731
for gen, tf in (("random", rt), ("genetic", lambda ds: "_gen2")):
    v = []
    for ds in DS:
        if gen == "random" and ds == "brfss2021":
            continue
        d = pd.read_csv(R / f"cross_{ds}{tf(ds)}_changes.csv")
        for m in ["published", "tableV", "route_A"]:
            S = sets(d[d["mode"] == m])
            v.append((ds, m, sum("Smoker" in s for s in S) / len(S)))
    pub = [x[2] for x in v if x[1] == "published"]
    print(f"VERIFY-DEF DiCE {gen}: published-only range {tr(100 * min(pub)):.2f}–{tr(100 * max(pub)):.2f}%; "
          f"configs x modes {tr(100 * min(x[2] for x in v)):.2f}–{tr(100 * max(x[2] for x in v)):.2f}%")
e = pd.concat([pd.read_csv(R / f"cross_{ds}_exh_changes.csv") for ds in DS])
Sp = sets(e[e["mode"] == "published"])
Sa = sets(e)
print(f"VERIFY-DEF exhaustive Smoker: published {tr(100 * sum('Smoker' in s for s in Sp) / len(Sp)):.2f}%; "
      f"all modes {tr(100 * sum('Smoker' in s for s in Sa) / len(Sa)):.2f}%")
# Re-audit of the DiCE counterfactuals with Smoker removed from the lever tier
orig = N.TIER["Smoker"]
diff = []
for gen, tf in (("random", lambda ds: "_xgbrand" if ds == "brfss2021" else rt(ds)), ("genetic", lambda ds: "_gen2")):
    for ds in DS:
        d = pd.read_csv(R / f"cross_{ds}{tf(ds)}_changes.csv")
        for m in ["published", "tableV", "route_A"]:
            S = sets(d[d["mode"] == m])
            N.TIER["Smoker"] = orig
            u0 = sum(classify(s, reading="narrow", rule="edge")["unsupported"] for s in S)
            N.TIER["Smoker"] = "immutable"
            u1 = sum(classify(s, reading="narrow", rule="edge")["unsupported"] for s in S)
            N.TIER["Smoker"] = orig
            if u0 != u1:
                diff.append((gen, ds, m, u0, u1, len(S)))
print("REAUDIT Smoker not a lever: configurations x modes with a different unsupported count:", diff if diff else "none")
