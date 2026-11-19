"""Pre-submission check of the graph/extraction numbers: Table 5, Section 3.3 scores, Supplementary S1, S2, S7, S9.
Sources: depgraph EDGES/TIER (code repo), outputs/edges_full.csv, killtest_x5/extraction/*_extractor_{A,B}.csv,
raw_cf_changes.csv (conference set), DiCE random result files (NHIS _v2, NHANES _v3)."""
import math
import sys
from pathlib import Path

import pandas as pd

P7 = Path("C:/Repos/uit/diabetes-xai-dependencygraph")
sys.path.insert(0, str(P7 / "src"))
import depgraph.audit as audit  # noqa: E402
from depgraph.edges import EDGES, Edge  # noqa: E402
from depgraph.nodes import TIER  # noqa: E402

H = Path("D:/20-study/uit/research/diabetesxai/paper7")
EX = H / "killtest_x5/extraction"
R = H / "outputs/p5_v10/outputs/crossdataset_p4/results"
IND = {f for f, t in TIER.items() if t == "indicator"}
MAPS = {"linear": {"A": .9, "B": .7, "C": .5, "E": .3, "explicit": .6, "narrative": .2},
        "conservative": {"A": .8, "B": .5, "C": .3, "E": .1, "explicit": .4, "narrative": .05},
        "permissive": {"A": .95, "B": .85, "C": .7, "E": .5, "explicit": .75, "narrative": .4}}


def tr(x, k):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


src_ok = [f for f, t in TIER.items() if t in ("lever", "treatable")]
dst_ok = [f for f, t in TIER.items() if t in ("lever", "treatable", "indicator")]
SPACE = [(u, v) for u in src_ok for v in dst_ok if u != v]
print("candidate space", len(SPACE))


def kappa(ea, eb):
    a = [p in ea for p in SPACE]; b = [p in eb for p in SPACE]
    n = len(SPACE); po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


cons = {}
for name, stem in (("MoH", "byt5481"), ("NICE", "nice_ng28"), ("WHO", "who_heartsd")):
    A, B = pd.read_csv(EX / f"{stem}_extractor_A.csv"), pd.read_csv(EX / f"{stem}_extractor_B.csv")
    ea, eb = set(zip(A.src, A.dst)), set(zip(B.src, B.dst))
    cons[name] = ea & eb
    k = kappa(ea, eb)
    print(f"{name}: A={len(ea)} B={len(eb)} agreed={len(ea & eb)} kappa={tr(k, 3) if k == k else 'undefined'} "
          f"into_ind={sorted(p for p in ea | eb if p[1] in IND)} agreed={sorted(ea & eb)} onlyone={sorted(ea ^ eb)}")

ada_pairs = {(e.src, e.dst) for e in EDGES}
print("ADA edges", len(EDGES), "pairs", len(ada_pairs), "into indicators",
      sorted((e.src, e.dst, e.grade) for e in EDGES if e.dst in IND))
print("MoH agreed subset of ADA:", cons["MoH"] <= ada_pairs, "WHO subset:", cons["WHO"] <= ada_pairs)

# S1 vs edges_full.csv and depgraph
ef = pd.read_csv(P7 / "outputs/edges_full.csv")
code = sorted((e.src, e.dst, e.grade) for e in EDGES)
csv = sorted((r.source, r.target, "-" if r.grade == "narrative" else r.grade) for r in ef.itertuples())
print("edges_full == depgraph EDGES (src,dst,grade):", code == csv or (code, csv))
sup = sorted(H.glob("thieuanhvan_diabetesxai_paper7_supplementary_hiss_en_v*.md"))[-1].read_text(encoding="utf-8")
s1 = [l for l in sup.split("\n") if l.startswith("| ") and l.split("|")[1].strip().isdigit()]
bad = []
for l in s1:
    c = [x.strip() for x in l.strip("|").split("|")]
    r = ef[ef.n == int(c[0])].iloc[0]
    exp = [f"{r.source} ({r.source_tier})", f"{r.target} ({r.target_tier})", r.grade]
    if c[1:4] != exp or c[5] != r.gloss or not c[4].startswith(r.ada_source.split(",")[0]):
        bad.append((c[0], c[1:6], exp, r.ada_source))
    if r.grade != "narrative" and c[4] != r.ada_source:
        bad.append(("loc", c[0], c[4], r.ada_source))
print("S1 rows", len(s1), "mismatches", bad)

# S2 matrix vs x5_edge_matrix.csv
mx = pd.read_csv(H / "killtest_x5/x5_edge_matrix.csv").fillna("")
s2 = [l for l in sup.split("\n") if " to " in l and l.startswith("| ") and ("indicator |" in l or "treatable |" in l or "lever |" in l)]
bad2 = []
for l in s2:
    c = [x.strip() for x in l.strip("|").split("|")]
    if len(c) != 6:
        continue
    e = c[0].replace(" to ", "->")
    r = mx[mx.edge == e]
    if r.empty:
        bad2.append(("missing", e)); continue
    r = r.iloc[0]
    exp = [r.tier_dst, r.ADA2026, r.MoH5481, r.NICE_NG28, r.WHO_HEARTSD]
    if c[1:] != exp:
        bad2.append((e, c[1:], exp))
print("S2 rows", len(s2), "matrix rows", len(mx), "mismatches", bad2)

# Table 5 audit + conference-set scores
ch = pd.read_csv(P7 / "outputs/raw_cf_changes.csv")
sets = list(ch.groupby(["query_i", "cf_k"]).feature.apply(set))
orig = list(EDGES)


def unsup(pairs, ss):
    audit.EDGES[:] = [Edge(u, v, "-", "x", "") for u, v in pairs]
    r = [audit.classify(s, reading="narrow", rule="edge")["unsupported"] for s in ss]
    audit.EDGES[:] = orig
    return r


base = unsup(ada_pairs, sets)
print("audited", len(sets), "touching", sum(bool(s & IND) for s in sets))
for g, p in (("ADA", ada_pairs), ("MoH", cons["MoH"]), ("WHO", cons["WHO"]), ("NICE", cons["NICE"]),
             ("union", ada_pairs | cons["MoH"] | cons["WHO"]), ("inter", ada_pairs & cons["MoH"] & cons["WHO"])):
    u = unsup(p, sets)
    print(f"  {g}: unsupported {sum(u)} flips {sum(a != b for a, b in zip(base, u))}")

ada_str = {}
for e in EDGES:
    g = "narrative" if e.grade == "-" else e.grade
    k = (e.src, e.dst)
    ada_str[k] = max([ada_str.get(k, "narrative"), g], key=lambda x: MAPS["linear"][x])


def scores(ss, m):
    vals, multi = [], 0
    for s in ss:
        t = s & IND
        if not t:
            continue
        per = []
        for v in t:
            ev = [MAPS[m][ada_str[(u, v)]] for u in s if (u, v) in ada_str and TIER.get(u) == "lever"]
            multi += len(ev) > 1
            c = 0.0
            for x in ev:
                c += x * (1 - c)
            per.append(c)
        vals.append(min(per))
    return pd.Series(vals), multi


for m in MAPS:
    sr, multi = scores(sets, m)
    print(f"conference {m}: n={len(sr)} zero={int((sr == 0).sum())} nonzero values={sorted(sr[sr > 0].unique())} "
          f"mean={tr(sr.mean(), 3)} multi-lever={multi}")

lo = []
for ds in ["nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c", "nhanes2021-2023_diag", "nhanes2021-2023_a1c"]:
    tag = "_v2" if ds.startswith("nhis") else "_v3"
    d = pd.read_csv(R / f"cross_{ds}{tag}_changes.csv")
    d = d[d["mode"] == "published"]
    ss = [set(str(x).split(";")) - {"", "nan"} for x in d.changed.fillna("")]
    sr, multi = scores(ss, "linear")
    lo.append((ds, tr((sr == 0).mean() * 100, 2), sr.max(), tr(sr.mean(), 4), multi))
for x in lo:
    print("  ", x)
print("zero share range", min(x[1] for x in lo), max(x[1] for x in lo), "mean range", min(x[3] for x in lo),
      max(x[3] for x in lo), "max score", max(x[2] for x in lo))
