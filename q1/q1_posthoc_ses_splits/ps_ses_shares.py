"""POST HOC (S-P1 companion), descriptive, read only: socio-economic changes in the existing counterfactual files.

For each change set S (features changed after rounding):
  ses_touch  S contains Education, Income or AnyHealthcare;
  ses_only   S is non-empty and contains only these features;
  no_action  S is non-empty and contains no lever and no treatable feature (graph roles).
Shares are reported at counterfactual level (all returned; valid only) and, for the exhaustive search, as the share
of patients whose best counterfactual (rank 0) is ses_only. CholCheck (diabetes, "monotonic up") is reported apart.
Also summarises the S-P1 (ses_freeze) and S-P2 (split_*) runs from their analysis JSON files when they exist.
Fractions with an exact rational value are computed with fractions.Fraction and truncated to 4 decimals.

Usage (P4 venv): python -I ps_ses_shares.py
"""
from __future__ import annotations

import json
import math
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, "C:/Repos/uit/diabetes-xai-dependencygraph/src")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "q1_domain_ckd"))

import pandas as pd  # noqa: E402

P7OUT = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs")
OUT = P7OUT / "q1_posthoc_ses_splits"
CKD = P7OUT / "q1_domain_ckd" / "a2_runs_main"
DIAB = P7OUT / "crossdataset_p4" / "results"
EXTB = P7OUT / "q1_ext_b"
SES = {"Education", "Income", "AnyHealthcare"}
SEEDS = [42, 123, 2024, 7, 31337]


def tr(fr) -> str:
    """Exact truncation of a Fraction (or float) to 4 decimals."""
    if fr is None:
        return "NA"
    if not isinstance(fr, Fraction):
        fr = Fraction(fr).limit_denominator(10**12)
    v = math.floor(fr * 10000) if fr >= 0 else -math.floor(-fr * 10000)
    s = "-" if v < 0 else ""
    v = abs(v)
    return f"{s}{v // 10000}.{v % 10000:04d}"


def sets(series):
    return [set(str(s).split(";")) - {"", "nan"} for s in series.fillna("")]


def block(S, role):
    n = len(S)
    if n == 0:
        return {"n": 0}
    touch = sum(bool(s & SES) for s in S)
    only = sum(bool(s) and s <= SES for s in S)
    noact = sum(bool(s) and not any(role.get(f) in ("lever", "treatable") for f in s) for s in S)
    chol = sum("CholCheck" in s for s in S)
    return {"n": n, "ses_touch": tr(Fraction(touch, n)), "ses_only": tr(Fraction(only, n)),
            "no_action": tr(Fraction(noact, n)), "cholcheck_touch": tr(Fraction(chol, n)),
            "counts": {"ses_touch": touch, "ses_only": only, "no_action": noact, "cholcheck": chol}}


def ckd():
    import a2_domain as D
    role = D.ROLE
    res = {}
    for mode in ("published", "lock", "route"):
        df = pd.concat([pd.read_csv(CKD / f"dice_{mode}_seed{s}.csv") for s in SEEDS], ignore_index=True)
        res[f"dice_{mode}_all"] = block(sets(df["changed"]), role)
        res[f"dice_{mode}_valid"] = block(sets(df[df["valid"] == 1]["changed"]), role)
    ex = pd.read_csv(CKD / "exhaustive.csv")
    for mode in ("published", "lock", "route"):
        e = ex[ex["mode"] == mode]
        res[f"exh_{mode}_all"] = block(sets(e["changed"]), role)
        b = e[e["round"] == 0]
        res[f"exh_{mode}_best"] = block(sets(b["changed"]), role)
    return res


def diabetes():
    from depgraph.nodes import TIER
    files = {"BRFSS 2021": "brfss2021_xgbrand", "NHIS 2022": "nhis2022_v2", "NHIS 2024": "nhis2024_v2",
             "NHANES 2017-2020 diagnosis": "nhanes2017-2020_diag_v3", "NHANES 2017-2020 HbA1c": "nhanes2017-2020_a1c_v3",
             "NHANES 2021-2023 diagnosis": "nhanes2021-2023_diag_v3", "NHANES 2021-2023 HbA1c": "nhanes2021-2023_a1c_v3"}
    exh = {k: v.replace("_v2", "").replace("_v3", "").replace("_xgbrand", "") + "_exh" for k, v in files.items()}
    res = {}
    for name, tag in files.items():
        df = pd.read_csv(DIAB / f"cross_{tag}_changes.csv")
        for mode, lab in (("published", "published"), ("tableV", "lock"), ("route_A", "route")):
            d = df[df["mode"] == mode]
            res[f"{name}|dice|{lab}|all"] = block(sets(d["changed"]), TIER)
            res[f"{name}|dice|{lab}|valid"] = block(sets(d[d["valid"] == 1]["changed"]), TIER)
        e = pd.read_csv(DIAB / f"cross_{exh[name]}_changes.csv")
        for mode, lab in (("published", "published"), ("tableV", "lock"), ("route_A", "route")):
            d = e[e["mode"] == mode]
            res[f"{name}|exh|{lab}|all"] = block(sets(d["changed"]), TIER)
            rank0 = d.groupby("pid").head(1)
            res[f"{name}|exh|{lab}|best"] = block(sets(rank0["changed"]), TIER)
    return res


def extb():
    from depgraph.nodes import TIER
    res = {}
    for name, fn, col in (("Actionable Recourse / LR", "ar_lr/out_{m}.csv", "valid_post"),
                          ("Growing Spheres / XGBoost", "gs_xgb/out_{m}.csv", "valid_post"),
                          ("Wachter / LR", "wachter_lr/kept_{m}.csv", None)):
        for m in ("published", "lock", "route"):
            p = EXTB / fn.format(m=m)
            if not p.exists():
                continue
            d = pd.read_csv(p)
            if col and col in d.columns:
                d = d[d[col].astype(bool)]
            res[f"{name}|{m}"] = block(sets(d["changed"]), TIER)
    mps = OUT / "ar_lr_mps"
    for m in ("published", "lock", "route"):
        p = mps / f"out_{m}.csv"
        if p.exists():
            d = pd.read_csv(p)
            d = d[d["valid_post"].astype(bool)]
            res[f"Actionable Recourse / LR, percentile cost (S-P3)|{m}"] = block(sets(d["changed"]), TIER)
    return res


def runs_summary():
    out = {}
    for d in sorted(OUT.glob("*")):
        f = d / "a2_analysis" / "results_main.json"
        if not f.exists():
            info = d / "a2_runs_main" / "run_info.json"
            if info.exists():
                j = json.loads(info.read_text(encoding="utf-8"))
                if str(j.get("status", "")).startswith("NOT REACHED"):
                    out[d.name] = {"status": j["status"], "test_auc": j["test_auc"]}
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        a1, a3, a5 = r["O_A1_fully_unactionable_dice_published"], r["O_A3_valid_among_requested_lock_minus_published"], \
            r["O_A5_dist_lock_minus_route_exhaustive"]
        out[d.name] = {
            "test_auc": r["test_auc"], "n_cohort": r["n_cohort"], "eligible": r["eligible"],
            "near_degenerate": r["near_degenerate_check"]["near_degenerate"],
            "O_A1": a1["est"], "O_A1_lower99": a1["lower_one_sided_99"], "O_share": r["O_A2_movability_null"]["T_mean_oshare"],
            "null": r["O_A2_movability_null"]["null_mean_of_means"], "p": r["O_A2_movability_null"]["p"],
            "H1_rule": r["H1"]["verdict"],
            "O_A3": a3["est"], "O_A3_lower99": a3["lower_one_sided_99"],
            "published_valid": a3["published_valid_among_requested"], "lock_valid": a3["lock_valid_among_requested"],
            "lock_coverage": r["H2"]["lock_coverage_point"], "H2_rule": r["H2"]["verdict"],
            "O_A5": a5["est"], "O_A5_ci98": a5["ci98"], "O_A5_share_zero": a5["share_exactly_zero"], "O_A5_n": a5["n"],
            "H3_rule": r["H3"]["verdict"], "O_A4": r["O_A4_route_strictly_better_than_lock"],
            "touch": r["touch_share_dice_published"]["est"],
            "unsupported_kdigo": r["leakage_published"]["dice_random"]["primary_kdigo_k1"]["est"],
            "software_checks": r["software_checks"],
            "single_nonindicator_flip": r["pre_generator_single_nonindicator_flip_share"],
            "exh_cov_lock": r["exhaustive_costs"]["lock"]["coverage"], "exh_cov_route": r["exhaustive_costs"]["route"]["coverage"],
            "kappa_ada_kdigo": r["A_Q4_cross_guideline_agreement"]["all_generators"]["kappa"]}
    return out


def main():
    res = {"ckd_a2_main": ckd(), "diabetes": diabetes(), "ext_b": extb(), "posthoc_runs": runs_summary()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ses_shares_and_runs.json").write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    c = res["ckd_a2_main"]
    for k in ("dice_published_all", "dice_lock_valid", "exh_lock_best"):
        print(k, c[k])


if __name__ == "__main__":
    main()
