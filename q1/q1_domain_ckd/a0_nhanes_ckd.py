"""A0: NHANES CKD analytic table with flow diagram (prereg v3 4.5).

Pools NHANES 2017-2020 (P_ files) and 2021-2023 (_L files). Features reuse the P7 recoders of the
nhanes-diabetes repository (load_cycle + build_cycle, the same code that built P7's NHANES tables),
plus the CKD-specific items below. No model is fitted here.

Order of the analytic sample (prereg 4.5, review fix N12):
  1 age >= 20; 2 RIDSTATR == 2; 3 RIDEXPRG != 1; 4 label rule; 5 complete cases on all features.
Label: positive if any available test is positive (eGFR < 60 by CKD-EPI 2021 creatinine, from LBXSCR;
or URDACT >= 30 mg/g); negative only if both tests are available and negative; missing otherwise.
Also runs the A0 gate checks on NHANES variable names (weights, labs, kidney questionnaire).
Usage: python -I a0_nhanes_ckd.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from q1_common import (NHANES_NEW_RAW, NHANES_P7_RAW, NHANES_REPO, OUT, below_normal, check_prereg, sha256_file,
                       trunc, write_json)

sys.path.insert(0, str(NHANES_REPO / "src"))
from nhanes_diabetes.encoding.core import build_cycle  # noqa: E402
from nhanes_diabetes.encoding.cycle_loader import load_cycle, read_xpt  # noqa: E402

DEST = OUT / "a0_nhanes_ckd"
CYCLES = {"2017-2020": {"code": 0, "files": {"BIOPRO": "P_BIOPRO", "ALB_CR": "P_ALB_CR", "TCHOL": "P_TCHOL", "KIQ_U": "P_KIQ_U"},
                        "weight": "WTMECPRP"},
          "2021-2023": {"code": 1, "files": {"BIOPRO": "BIOPRO_L", "ALB_CR": "ALB_CR_L", "TCHOL": "TCHOL_L", "KIQ_U": "KIQ_U_L"},
                        "weight": "WTMEC2YR"}}
FEATURES = ["Diabetes", "HighBP", "HighChol", "BMI", "Smoker", "PhysActivity", "GenHlth", "MentHlth", "Stroke",
            "HeartDiseaseorAttack", "Age", "Sex", "Education", "Income", "AnyHealthcare", "Cycle"]
REQUIRED_RAW = {"DEMO": ["SEQN", "RIDAGEYR", "RIAGENDR", "RIDSTATR", "RIDEXPRG"], "BIOPRO": ["SEQN", "LBXSCR"],
                "ALB_CR": ["SEQN", "URDACT"], "TCHOL": ["SEQN", "LBXTC"], "KIQ_U": ["SEQN", "KIQ022"],
                "SMQ": ["SEQN", "SMQ020", "SMQ040"], "BPXO": ["SEQN", "BPXOSY1", "BPXOSY2", "BPXOSY3"],
                "DIQ": ["SEQN", "DIQ010"], "BPQ": ["SEQN", "BPQ020", "BPQ080"], "HUQ": ["SEQN", "HUQ010"],
                "MCQ": ["SEQN", "MCQ160F", "MCQ160C", "MCQ160E"]}


def egfr_ckdepi2021(scr, age, female):
    """CKD-EPI 2021 creatinine equation (race-free), mL/min/1.73 m2."""
    kappa = np.where(female, 0.7, 0.9)
    alpha = np.where(female, -0.241, -0.302)
    r = scr / kappa
    return (142 * np.minimum(r, 1) ** alpha * np.maximum(r, 1) ** -1.200 * 0.9938 ** age
            * np.where(female, 1.012, 1.0))


def yes_no(s):
    s = pd.to_numeric(s, errors="coerce")
    return pd.Series(np.select([s == 1, s == 2], [1.0, 0.0], np.nan), index=s.index)


def build(cycle: str, gate: dict) -> tuple[pd.DataFrame, list]:
    cfg = CYCLES[cycle]
    joined, status = load_cycle(cycle, NHANES_P7_RAW)
    base, prov = build_cycle(joined, cycle)  # P7 recoders, before P7's own finalize()
    extra = {}
    for t, fn in cfg["files"].items():
        d = read_xpt(NHANES_NEW_RAW / cycle / f"{fn}.xpt")
        extra[t] = d
    names = {"DEMO": set(joined.columns)}
    names.update({t: set(d.columns) for t, d in extra.items()})
    for t in ("SMQ", "BPXO", "DIQ", "BPQ", "HUQ", "MCQ"):
        names[t] = set(joined.columns)
    missing = {t: [v for v in vs if v not in names[t]] for t, vs in REQUIRED_RAW.items()}
    gate[cycle] = {"weight_variable_expected": cfg["weight"], "weight_variable_present": cfg["weight"] in joined.columns,
                   "missing_required_variables": {k: v for k, v in missing.items() if v},
                   "p7_tables_loaded": status,
                   "p7_provenance": {k: prov[k] for k in ("PhysActivity", "MentHlth", "GenHlth", "Education", "Income",
                                                          "AnyHealthcare", "Stroke", "HeartDiseaseorAttack", "BMI")}}
    if any(missing.values()) or not gate[cycle]["weight_variable_present"]:
        raise SystemExit(f"A0 gate failed for {cycle}: {gate[cycle]}")

    j = joined.copy()
    for t, d in extra.items():
        cols = [c for c in d.columns if c in {v for vs in REQUIRED_RAW.values() for v in vs} and c != "SEQN"]
        j = j.merge(d[["SEQN"] + cols], on="SEQN", how="left", validate="one_to_one")
    df = pd.DataFrame({"SEQN": j["SEQN"].astype("int64")})
    for c in ("BMI", "PhysActivity", "GenHlth", "MentHlth", "Stroke", "HeartDiseaseorAttack", "Age", "Sex",
              "Education", "Income", "AnyHealthcare"):
        df[c] = base[c].values
    df["BMI"] = df["BMI"].round(0)  # P7 NHANES convention (p7_cross_p4pipeline.load): integer BMI
    diq = pd.to_numeric(j["DIQ010"], errors="coerce")
    df["Diabetes"] = np.select([diq == 1, diq.isin([2, 3])], [1.0, 0.0], np.nan)
    df["Diabetes_borderline_as_yes"] = np.select([diq.isin([1, 3]), diq == 2], [1.0, 0.0], np.nan)
    sbp = j[["BPXOSY1", "BPXOSY2", "BPXOSY3"]].apply(pd.to_numeric, errors="coerce")
    msbp = sbp.mean(axis=1, skipna=True)
    df["SBP_mean"] = msbp.values
    df["HighBP"] = np.where(msbp.isna(), np.nan, (msbp >= 130).astype(float))
    tc = pd.to_numeric(j["LBXTC"], errors="coerce")
    df["HighChol"] = np.where(tc.isna(), np.nan, (tc >= 240).astype(float))
    s20, s40 = pd.to_numeric(j["SMQ020"], errors="coerce"), pd.to_numeric(j["SMQ040"], errors="coerce")
    df["Smoker"] = np.select([s20 == 2, (s20 == 1) & s40.isin([1, 2]), (s20 == 1) & (s40 == 3)], [0.0, 1.0, 0.0], np.nan)
    df["Cycle"] = float(cfg["code"])
    # auxiliary (not features)
    df["BPQ020_toldHighBP"] = yes_no(j["BPQ020"]).values
    df["BPQ080_toldHighChol"] = yes_no(j["BPQ080"]).values
    df["KIQ022_weakfailingkidneys"] = yes_no(j["KIQ022"]).values
    df["WTMEC"] = pd.to_numeric(j[cfg["weight"]], errors="coerce").values
    df["WTMEC_name"] = cfg["weight"]
    for c in ("SDMVPSU", "SDMVSTRA"):
        df[c] = pd.to_numeric(j[c], errors="coerce").values
    age = pd.to_numeric(j["RIDAGEYR"], errors="coerce")
    female = pd.to_numeric(j["RIAGENDR"], errors="coerce") == 2
    scr = pd.to_numeric(j["LBXSCR"], errors="coerce")
    df["LBXSCR"] = scr.values
    df["eGFR_ckdepi2021"] = np.where(scr.notna() & age.notna(), egfr_ckdepi2021(scr.values, age.values, female.values), np.nan)
    df["URDACT"] = pd.to_numeric(j["URDACT"], errors="coerce").values
    eg_pos = df["eGFR_ckdepi2021"] < 60
    ac_pos = df["URDACT"] >= 30
    eg_av, ac_av = df["eGFR_ckdepi2021"].notna(), df["URDACT"].notna()
    df["CKD_label"] = np.select([(eg_av & eg_pos) | (ac_av & ac_pos), eg_av & ac_av], [1.0, 0.0], np.nan)

    flow = []
    d0 = df.copy()
    flow.append(("all participants in DEMO", len(d0)))
    d1 = d0[age.values >= 20]
    flow.append(("1 aged 20 years or older", len(d1)))
    ridstatr = pd.to_numeric(j["RIDSTATR"], errors="coerce").values
    d2 = d1[ridstatr[d1.index] == 2]
    flow.append(("2 examined at the MEC (RIDSTATR = 2)", len(d2)))
    preg = pd.to_numeric(j["RIDEXPRG"], errors="coerce").values
    d3 = d2[preg[d2.index] != 1]
    flow.append(("3 not pregnant (RIDEXPRG != 1)", len(d3)))
    nolab = d3["CKD_label"].isna()
    flow.append(("   excluded: label missing (no positive test and not both tests available)", int(nolab.sum())))
    flow.append(("      of which: no eGFR and no ACR", int((nolab & d3.eGFR_ckdepi2021.isna() & d3.URDACT.isna()).sum())))
    flow.append(("      of which: eGFR negative, ACR missing", int((nolab & d3.eGFR_ckdepi2021.notna() & d3.URDACT.isna()).sum())))
    flow.append(("      of which: ACR negative, eGFR missing", int((nolab & d3.eGFR_ckdepi2021.isna() & d3.URDACT.notna()).sum())))
    d4 = d3[~nolab]
    flow.append(("4 label available", len(d4)))
    miss = d4[FEATURES].isna()
    for f in FEATURES:
        flow.append((f"   missing {f}", int(miss[f].sum())))
    d5 = d4[~miss.any(axis=1)].copy()
    flow.append(("5 complete cases on all features (analytic sample)", len(d5)))
    flow.append(("   label positive", int((d5.CKD_label == 1).sum())))
    flow.append(("   label negative", int((d5.CKD_label == 0).sum())))
    return d5, flow, base, j


def p7_consistency(cycle: str, base: pd.DataFrame, j: pd.DataFrame) -> dict:
    """The rebuilt P7 features must equal P7's own NHANES table for the same SEQN (same recoders, this venv)."""
    p7 = pd.read_csv(NHANES_REPO / "outputs" / "tabular" / f"cdc_nhanes_diabetes_{cycle}.csv")
    b = base.copy()
    b["SEQN"] = j["SEQN"].astype("int64").values
    m = p7.merge(b, on="SEQN", suffixes=("_p7", "_new"))
    res = {"n_matched": len(m), "n_p7": len(p7)}
    for c in ("HighBP", "HighChol", "BMI", "Smoker", "Stroke", "HeartDiseaseorAttack", "PhysActivity",
              "AnyHealthcare", "GenHlth", "MentHlth", "Sex", "Age", "Education", "Income"):
        a, z = m[f"{c}_p7"].astype(float), m[f"{c}_new"].astype(float)
        if c == "BMI":
            z = z.round(2)
        res[c] = int(((a - z).abs() > 1e-9).sum() + (a.isna() != z.isna()).sum())
    return res


def main():
    below_normal()
    check_prereg()
    DEST.mkdir(parents=True, exist_ok=True)
    gate, parts, flows, cons = {}, [], {}, {}
    for cycle in CYCLES:
        d5, flow, base, j = build(cycle, gate)
        parts.append(d5)
        flows[cycle] = flow
        cons[cycle] = p7_consistency(cycle, base, j)
    pooled = pd.concat(parts, ignore_index=True)
    cols = ["SEQN", "CKD_label"] + FEATURES + ["Diabetes_borderline_as_yes", "BPQ020_toldHighBP", "BPQ080_toldHighChol",
                                              "KIQ022_weakfailingkidneys", "WTMEC", "WTMEC_name", "SDMVPSU", "SDMVSTRA",
                                              "SBP_mean", "LBXSCR", "eGFR_ckdepi2021", "URDACT"]
    pooled = pooled[cols].sort_values(["Cycle", "SEQN"]).reset_index(drop=True)
    for c in ["CKD_label"] + FEATURES:
        if c not in ("BMI", "Age"):
            pooled[c] = pooled[c].astype(int)
    pooled["BMI"] = pooled["BMI"].astype(int)
    pooled["Age"] = pooled["Age"].astype(int)
    out_csv = DEST / "nhanes_ckd_analytic_2017-2023.csv"
    pooled.to_csv(out_csv, index=False, lineterminator="\n", float_format="%.6f")
    n = len(pooled)
    lines = ["# NHANES CKD analytic sample: flow (prereg v3 4.5)", "",
             "Pooled NHANES 2017-2020 (P_ files) and 2021-2023 (_L files). Counts are participants.", ""]
    for cycle, flow in flows.items():
        lines += [f"## {cycle}", "", "| Step | n |", "|---|---|"] + [f"| {s} | {k} |" for s, k in flow] + [""]
    lines += ["## Pooled", "", f"| analytic sample | {n} |", "|---|---|",
              f"| label positive | {int((pooled.CKD_label == 1).sum())} |",
              f"| label negative | {int((pooled.CKD_label == 0).sum())} |",
              f"| share positive (truncated) | {trunc(float((pooled.CKD_label == 1).mean()))} |",
              f"| with KIQ022 = 1 (excluded in the less-exposed cohort) | {int((pooled.KIQ022_weakfailingkidneys == 1).sum())} |", ""]
    (DEST / "nhanes_ckd_flow.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(DEST / "nhanes_ckd_flow.json", {"flow": flows, "pooled_n": n})
    import subprocess
    commit = subprocess.run(["git", "-C", str(NHANES_REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(NHANES_REPO), "status", "--short", "src"], capture_output=True, text=True).stdout.strip()
    write_json(DEST / "a0_gate_nhanes.json", {"nhanes_diabetes_commit": commit, "nhanes_diabetes_src_uncommitted": dirty,
                                               "gate": gate, "p7_feature_consistency_mismatches": cons,
                                               "analytic_csv": str(out_csv), "analytic_csv_sha256": sha256_file(out_csv)})
    print("\n".join(lines))
    print("consistency", cons)


if __name__ == "__main__":
    main()
