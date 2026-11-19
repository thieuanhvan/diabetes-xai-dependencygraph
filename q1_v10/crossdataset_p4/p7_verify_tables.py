"""Pre-submission check: rebuild main Tables 3, 6, 7 and Supplementary Table S11 from the locked per-counterfactual
result files and compare every cell with the manuscript/supplementary markdown (truncated values, as reported).

Locked tags: DiCE random NHIS _v2, NHANES _v3; DiCE genetic _gen2; exhaustive _exh.
Point estimates and 95% intervals are recomputed with the same patient bootstrap (2,000 resamples, same RNG seeds)
as p7_cross_bootstrap.py / p7_exh_bootstrap.py, independently of the stored bootstrap CSV files.
Usage: python p7_verify_tables.py <manuscript.md> <supplementary.md>
"""
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
from depgraph.audit import classify  # noqa: E402

R = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4") / "results"
B = 2000
NAMES = {"BRFSS 2021": "brfss2021", "NHIS 2022": "nhis2022", "NHIS 2024": "nhis2024",
         "NHANES 2017–2020, diagnosis": "nhanes2017-2020_diag", "NHANES 2017–2020, HbA1c": "nhanes2017-2020_a1c",
         "NHANES 2021–2023, diagnosis": "nhanes2021-2023_diag", "NHANES 2021–2023, HbA1c": "nhanes2021-2023_a1c"}
RANDOM_TAG = lambda ds: "_v2" if ds.startswith("nhis") else "_v3"  # noqa: E731


def tr(x, k):
    # round away binary noise before truncating (0.3224 * 100 = 32.239999... must truncate to 32.24)
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


def f4(x):
    return f"{tr(x, 4):.4f}".replace("-", "−")


def pct(x):
    return f"{tr(x * 100, 2):.2f}%"


def ci(e, lo, hi):
    return f"{f4(e)} [{f4(lo)}, {f4(hi)}]"


def classified(f):
    df = pd.read_csv(f)
    sets = [set(str(s).split(";")) - {"", "nan"} for s in df.changed.fillna("")]
    cl = [classify(s, reading="narrow", rule="edge") for s in sets]
    return df.assign(touch=[r["touches_target"] for r in cl], unsup=[r["unsupported"] for r in cl],
                     fully=[r["fully_unactionable"] for r in cl])


def boot(x, idx):
    bs = np.array([np.nanmean(x[i]) for i in idx])
    return np.nanmean(x), np.quantile(bs, .025), np.quantile(bs, .975)


def dice_rows(tag_of, seed=20261015):
    out = {}
    for lab, ds in NAMES.items():
        f = R / f"cross_{ds}{tag_of(ds)}_changes.csv"
        if not f.exists():
            continue
        df = classified(f)
        s = pd.read_csv(R / f"cross_{ds}{tag_of(ds)}_summary.csv")
        pp = df.groupby(["mode", "pid"])[["valid", "touch", "unsup", "fully"]].mean()
        pats = pp.loc["published"].index.to_numpy()
        rng = np.random.default_rng(seed)
        idx = [rng.choice(len(pats), len(pats), replace=True) for _ in range(B)]
        pub = pp.loc["published"].reindex(pats)
        cells = {"n": str(int(s.cohort.iloc[0])), "Validity": f4(pub.valid.mean())}
        for k, c in (("Touch indicator", "touch"), ("Unsupported", "unsup"), ("Fully unactionable", "fully")):
            cells[k] = pct(pub[c].mean())
        for k, mode in (("Δ indicator lock", "tableV"), ("Δ route-aware", "route_A")):
            d = (pp.loc[mode].reindex(pats).valid - pub.valid).to_numpy()
            cells[k] = ci(*boot(d, idx))
            cells[k + " paired n"] = int((~np.isnan(d)).sum())
        # pooled-over-CF alternatives, to see which estimand a cell uses
        p = df[df["mode"] == "published"]
        cells["_pooled"] = {"Validity": f4(p.valid.mean()), "Touch indicator": pct(p.touch.mean()),
                            "Unsupported": pct(p.unsup.mean()), "Fully unactionable": pct(p.fully.mean())}
        out[lab] = cells
    return out


def exh_rows(seed=20261018):
    out = {}
    for lab, ds in NAMES.items():
        df = classified(R / f"cross_{ds}_exh_changes.csv")
        share = df.groupby(["mode", "pid"])[["touch", "unsup", "fully"]].mean()
        best = df.sort_values(["n_changes", "dist"]).groupby(["mode", "pid"]).first()[["n_changes", "dist"]]
        pp = share.join(best)
        pats = pp.loc["published"].index.to_numpy()
        rng = np.random.default_rng(seed)
        idx = [rng.choice(len(pats), len(pats), replace=True) for _ in range(B)]
        pub = pp.loc["published"].reindex(pats)
        cells = {"n": str(len(pats)), "Touch indicator": pct(pub.touch.mean()), "Unsupported": pct(pub.unsup.mean()),
                 "Fully unactionable": pct(pub.fully.mean()), "Changes, best CF": f4(pub.n_changes.mean()),
                 "Distance, best CF": f4(pub.dist.mean())}
        for k, mode in (("Δ distance, lock", "tableV"), ("Δ distance, route-aware", "route_A")):
            d = (pp.loc[mode].reindex(pats).dist - pub.dist).to_numpy()
            cells[k] = ci(*boot(d, idx))
        p = df[df["mode"] == "published"]
        cells["_pooled"] = {"Touch indicator": pct(p.touch.mean()), "Unsupported": pct(p.unsup.mean()),
                            "Fully unactionable": pct(p.fully.mean())}
        out[lab] = cells
    return out


def md_table(text, caption_start):
    i = text.index(caption_start)
    lines = text[i:].split("\n")
    rows = [l for l in lines[1:40] if l.startswith("|")]
    end = next(k for k, l in enumerate(lines[2:], 2) if l.startswith("|"))
    block = []
    for l in lines[end:]:
        if not l.startswith("|"):
            break
        block.append([c.strip() for c in l.strip("|").split("|")])
    head, body = block[0], block[2:]
    return head, body


def compare(name, head, body, rebuilt, report):
    for r in body:
        lab = r[0]
        key = next((k for k in rebuilt if k == lab), None)
        if key is None:
            continue
        for h, v in zip(head[1:], r[1:]):
            if h not in rebuilt[key]:
                continue
            want = rebuilt[key][h]
            alt = rebuilt[key].get("_pooled", {}).get(h)
            v2 = v.replace("+", "")
            ok = v2 == want.replace("+", "")
            note = "" if ok else (" (matches pooled-over-CF)" if alt and v2 == alt else "")
            report.append((name, lab, h, v, want, "OK" if ok else "DIFF" + note))


def s11(sup_text, report):
    i = sup_text.index("*Table S11.")
    rows = [l for l in sup_text[i:].split("\n") if l.startswith("| DiCE")]
    for tag, gen in (("random", "DiCE random"), ("_gen2", "DiCE genetic")):
        recs = {}
        for lab, ds in NAMES.items():
            t = RANDOM_TAG(ds) if tag == "random" else tag
            f = R / f"cross_{ds}{t}_changes.csv"
            if not f.exists() or (tag == "random" and ds == "brfss2021"):
                continue
            d = classified(f)
            d = d.assign(sup=(d.valid == 1) & ~d.unsup)
            s = pd.read_csv(R / f"cross_{ds}{t}_summary.csv")
            for mode, mn in (("published", "published"), ("tableV", "indicator lock"), ("route_A", "route-aware")):
                m = d[d["mode"] == mode]
                cells = int(s.cohort.iloc[0]) * s[s["mode"] == mode].seed.nunique()
                per = m.groupby(["pid", "seed"]).agg(k=("sup", "sum"))
                recs[(lab, mn)] = [f"{len(m)}/{cells * 5}", pct(len(per) / cells), pct((per.k > 0).sum() / cells),
                                   f"{tr(per.k.sum() / cells / 5, 4):.4f}"]
        for l in rows:
            c = [x.strip() for x in l.strip("|").split("|")]
            if c[0] != gen:
                continue
            want = recs.get((c[1], c[2]))
            if want is None:
                report.append(("S11", f"{gen} {c[1]}", c[2], "|".join(c[3:]), "-", "NO SOURCE"))
                continue
            report.append(("S11", f"{gen} {c[1]}", c[2], " | ".join(c[3:]), " | ".join(want),
                           "OK" if c[3:] == want else "DIFF"))


def table2_rows():
    """BRFSS DiCE random, conference runner outputs: means over the five seeds; shares over returned CFs."""
    e = pd.read_csv("C:/Repos/uit/diabetes-xai-dependencygraph/outputs/route_enforcement.csv")
    lab = {"baseline_published": "Published", "route_A_lever": "Route-aware (levers)",
           "route_B_lever_treatable": "Route-aware (levers and treatable)",
           "route_C_lever_graded": "Route-aware (graded edges only)"}
    out = {}
    for k, v in lab.items():
        x = e[e.label == k]
        out[v] = {"Validity": f4(x.validity.mean()),
                  "Touch indicator": pct((x.cf_touching_indicator / x.n_cf).mean()),
                  "Unsupported": pct((x.unsupported_edge_rule / x.n_cf).mean()),
                  "Fully unactionable": pct((x.fully_unactionable / x.n_cf).mean()),
                  "Mean rounds": f4(x.rounds_mean.mean())}
    return out


def table4_rows():
    """Gain shares from nhis_diagnosis.csv; BMI-changing CF shares and validity from the DiCE random files."""
    g = pd.read_csv(R.parent / "nhis_diagnosis.csv").set_index("dataset")
    out = {}
    for lab, ds in NAMES.items():
        if ds not in g.index or "2021" in ds:
            continue
        c = {"Gain BMI": pct(g.loc[ds, "gain_share_BMI"]), "Gain indicators": pct(g.loc[ds, "gain_share_indicators"])}
        f = R / f"cross_{ds}{RANDOM_TAG(ds)}_changes.csv"
        if ds != "brfss2021" and f.exists():
            d = pd.read_csv(f)
            d = d.assign(bmi=d.changed.fillna("").str.split(";").apply(lambda s: "BMI" in s))
            p, lk = d[d["mode"] == "published"], d[d["mode"] == "tableV"]
            c["CF changing BMI, published to lock"] = f"{pct(p.bmi.mean())} to {pct(lk.bmi.mean())}"
            c["Validity if BMI changed"] = f4(lk[lk.bmi].valid.mean())
            c["Validity if not"] = f4(lk[~lk.bmi].valid.mean())
        out[lab] = c
    return out


def table5_check(report):
    e = pd.read_csv("C:/Repos/uit/diabetes-xai-dependencygraph/outputs/route_enforcement.csv")
    b = e[(e.label == "baseline_published") & (e.seed == 42)].iloc[0]
    report.append(("Table 5", "ADA", "Unsupported counterfactuals", "210", str(int(b.unsupported_edge_rule)),
                   "OK" if int(b.unsupported_edge_rule) == 210 else "DIFF"))
    report.append(("Table 5", "other authorities", "Unsupported (= indicator-touching CFs)", "330",
                   str(int(b.cf_touching_indicator)), "OK" if int(b.cf_touching_indicator) == 330 else "DIFF"))
    raw = pd.read_csv("C:/Repos/uit/diabetes-xai-dependencygraph/outputs/raw_cf_changes.csv")
    k = raw.groupby(["query_i", "cf_k"]).ngroups
    report.append(("Table 5", "all", "Re-audited CFs (change at least one feature)", "988", str(k),
                   "OK" if k == 988 else "DIFF"))


def main():
    man = Path(sys.argv[1]).read_text(encoding="utf-8")
    sup = Path(sys.argv[2]).read_text(encoding="utf-8")
    rep = []
    compare("Table 2", *md_table(man, "*Table 2."), table2_rows(), rep)
    compare("Table 4", *md_table(man, "*Table 4."), table4_rows(), rep)
    table5_check(rep)
    rnd, gen, exh = dice_rows(RANDOM_TAG), dice_rows(lambda ds: "_gen2"), exh_rows()
    compare("Table 3", *md_table(man, "*Table 3."), rnd, rep)
    compare("Table 6", *md_table(man, "*Table 6."), gen, rep)
    compare("Table 7", *md_table(man, "*Table 7."), exh, rep)
    s11(sup, rep)
    out = pd.DataFrame(rep, columns=["table", "row", "column", "manuscript", "rebuilt", "status"])
    out.to_csv(Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4") / "verify_tables_report.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 60, "display.max_rows", 500)
    print(out.status.value_counts().to_string())
    print(out[out.status != "OK"].to_string(index=False))
    print("\npaired n, genetic route-aware:",
          {k: v["Δ route-aware paired n"] for k, v in gen.items()})


if __name__ == "__main__":
    main()
