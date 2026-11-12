"""A0-HTN: NHANES hypertension analytic table with flow diagram (addendum HTN v1, section 4).

Pools NHANES 2017-2020 (P_ files) and 2021-2023 (_L files), the same cycles, raw files and recoders as the
CKD table (q1_domain_ckd/a0_nhanes_ckd.py): load_cycle + build_cycle of the nhanes-diabetes repository
(PhysActivity 2021-2023 by the corrected rule recode_phys_activity_gpaq_v2, commit 778be1a, deviation O1-res).
No model is fitted here.

Feature schema = CKD schema with HighBP removed (it is the outcome) and KidneyDisease (KIQ022) added as an
immutable diagnosis-history item. Income, Education and AnyHealthcare are kept as features; their direction is
fixed to immutable by the role table (a0_role_table_htn.py), not here.

Order of the analytic sample:
  1 age >= 20; 2 RIDSTATR == 2; 3 RIDEXPRG != 1; 4 primary label available; 5 complete cases on all features.
Primary label L1 (measured): mean of the available oscillometric readings, at least 2 valid readings for each of
systolic (BPXOSY1-3) and diastolic (BPXODI1-3); positive if mean SBP >= 130 or mean DBP >= 80 mmHg (stage 1 or
higher in the ACC/AHA classification); negative only if both means are available and below; missing otherwise.
Secondary label L2 (measured or treated): L1 positive or now taking prescribed medicine for high blood pressure
(2017-2020 BPQ050A = 1; 2021-2023 BPQ150 = 1); negative if L1 negative and medication use is known to be no;
missing otherwise.
Usage: python -I a0_nhanes_htn.py
"""
from __future__ import annotations

import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))  # python -I omits the script dir
from htn_common import (CKD_TOOLS, NHANES_NEW_RAW, NHANES_P7_RAW, NHANES_REPO, OUT, below_normal, check_prereg,
                        sha256_file, trunc, write_json)

sys.path.insert(0, str(NHANES_REPO / "src"))
sys.path.insert(0, str(CKD_TOOLS))
from nhanes_diabetes.encoding.core import build_cycle  # noqa: E402
from nhanes_diabetes.encoding.cycle_loader import load_cycle, read_xpt  # noqa: E402
from a0_nhanes_ckd import p7_consistency, yes_no  # noqa: E402  (CKD helpers, read only)

DEST = OUT / "a0_nhanes_htn"
CYCLES = {"2017-2020": {"code": 0, "files": {"TCHOL": "P_TCHOL", "KIQ_U": "P_KIQ_U"}, "weight": "WTMECPRP",
                        "med_now": "BPQ050A", "med_told": "BPQ040A"},
          "2021-2023": {"code": 1, "files": {"TCHOL": "TCHOL_L", "KIQ_U": "KIQ_U_L"}, "weight": "WTMEC2YR",
                        "med_now": "BPQ150", "med_told": None}}
FEATURES = ["Diabetes", "HighChol", "BMI", "Smoker", "PhysActivity", "GenHlth", "MentHlth", "Stroke",
            "HeartDiseaseorAttack", "KidneyDisease", "Age", "Sex", "Education", "Income", "AnyHealthcare", "Cycle"]
SBP = ["BPXOSY1", "BPXOSY2", "BPXOSY3"]
DBP = ["BPXODI1", "BPXODI2", "BPXODI3"]
MIN_READINGS = 2


def required(cfg):
    req = {"DEMO": ["SEQN", "RIDAGEYR", "RIAGENDR", "RIDSTATR", "RIDEXPRG"], "TCHOL": ["SEQN", "LBXTC"],
           "KIQ_U": ["SEQN", "KIQ022"], "SMQ": ["SEQN", "SMQ020", "SMQ040"], "BPXO": ["SEQN"] + SBP + DBP,
           "DIQ": ["SEQN", "DIQ010"], "BPQ": ["SEQN", "BPQ020", "BPQ080", cfg["med_now"]]
           + ([cfg["med_told"]] if cfg["med_told"] else []),
           "HUQ": ["SEQN", "HUQ010"], "MCQ": ["SEQN", "MCQ160F", "MCQ160C", "MCQ160E"]}
    return req


def build(cycle: str, gate: dict):
    cfg = CYCLES[cycle]
    req = required(cfg)
    joined, status = load_cycle(cycle, NHANES_P7_RAW)
    base, prov = build_cycle(joined, cycle)  # P7 recoders (PhysActivity 2021-2023 = gpaq_v2 since 778be1a)
    extra = {t: read_xpt(NHANES_NEW_RAW / cycle / f"{fn}.xpt") for t, fn in cfg["files"].items()}
    names = {"DEMO": set(joined.columns)}
    names.update({t: set(d.columns) for t, d in extra.items()})
    for t in ("SMQ", "BPXO", "DIQ", "BPQ", "HUQ", "MCQ"):
        names[t] = set(joined.columns)
    missing = {t: [v for v in vs if v not in names[t]] for t, vs in req.items()}
    gate[cycle] = {"weight_variable_expected": cfg["weight"], "weight_variable_present": cfg["weight"] in joined.columns,
                   "missing_required_variables": {k: v for k, v in missing.items() if v},
                   "p7_tables_loaded": status,
                   "p7_provenance": {k: prov[k] for k in ("PhysActivity", "MentHlth", "GenHlth", "Education", "Income",
                                                          "AnyHealthcare", "Stroke", "HeartDiseaseorAttack", "BMI")}}
    if any(missing.values()) or not gate[cycle]["weight_variable_present"]:
        raise SystemExit(f"A0-HTN gate failed for {cycle}: {gate[cycle]}")

    j = joined.copy()
    for t, d in extra.items():
        cols = [c for c in req[t] if c != "SEQN"]
        j = j.merge(d[["SEQN"] + cols], on="SEQN", how="left", validate="one_to_one")
    df = pd.DataFrame({"SEQN": j["SEQN"].astype("int64")})
    for c in ("BMI", "PhysActivity", "GenHlth", "MentHlth", "Stroke", "HeartDiseaseorAttack", "Age", "Sex",
              "Education", "Income", "AnyHealthcare"):
        df[c] = base[c].values
    df["BMI"] = df["BMI"].round(0)  # P7 NHANES convention: integer BMI (as CKD)
    diq = pd.to_numeric(j["DIQ010"], errors="coerce")
    df["Diabetes"] = np.select([diq == 1, diq.isin([2, 3])], [1.0, 0.0], np.nan)
    df["Diabetes_borderline_as_yes"] = np.select([diq.isin([1, 3]), diq == 2], [1.0, 0.0], np.nan)
    tc = pd.to_numeric(j["LBXTC"], errors="coerce")
    df["HighChol"] = np.where(tc.isna(), np.nan, (tc >= 240).astype(float))
    s20, s40 = pd.to_numeric(j["SMQ020"], errors="coerce"), pd.to_numeric(j["SMQ040"], errors="coerce")
    df["Smoker"] = np.select([s20 == 2, (s20 == 1) & s40.isin([1, 2]), (s20 == 1) & (s40 == 3)], [0.0, 1.0, 0.0], np.nan)
    df["KidneyDisease"] = yes_no(j["KIQ022"]).values
    df["Cycle"] = float(cfg["code"])

    # blood pressure: outcome, never a feature
    sbp = j[SBP].apply(pd.to_numeric, errors="coerce")
    dbp = j[DBP].apply(pd.to_numeric, errors="coerce")
    n_s, n_d = sbp.notna().sum(axis=1), dbp.notna().sum(axis=1)
    msbp = sbp.mean(axis=1, skipna=True).where(n_s >= MIN_READINGS)
    mdbp = dbp.mean(axis=1, skipna=True).where(n_d >= MIN_READINGS)
    df["SBP_mean"], df["DBP_mean"] = msbp.values, mdbp.values
    df["n_SBP_readings"], df["n_DBP_readings"] = n_s.values, n_d.values
    pos = (msbp.notna() & (msbp >= 130)) | (mdbp.notna() & (mdbp >= 80))
    both = msbp.notna() & mdbp.notna()
    df["HTN_L1_measured"] = np.select([pos, both], [1.0, 0.0], np.nan)
    told = pd.to_numeric(j["BPQ020"], errors="coerce")
    now = pd.to_numeric(j[cfg["med_now"]], errors="coerce")
    med_no = (told == 2) | (now == 2)
    if cfg["med_told"]:
        med_no = med_no | (pd.to_numeric(j[cfg["med_told"]], errors="coerce") == 2)
    med = pd.Series(np.select([now == 1, med_no], [1.0, 0.0], np.nan), index=j.index)
    df["BP_med_now"] = med.values
    l1 = df["HTN_L1_measured"]
    df["HTN_L2_measured_or_treated"] = np.select([(l1 == 1) | (med.values == 1), (l1 == 0) & (med.values == 0)],
                                                 [1.0, 0.0], np.nan)
    # auxiliary (not features)
    df["BPQ020_toldHighBP"] = yes_no(j["BPQ020"]).values
    df["BPQ080_toldHighChol"] = yes_no(j["BPQ080"]).values
    df["WTMEC"] = pd.to_numeric(j[cfg["weight"]], errors="coerce").values
    df["WTMEC_name"] = cfg["weight"]
    for c in ("SDMVPSU", "SDMVSTRA"):
        df[c] = pd.to_numeric(j[c], errors="coerce").values
    df["LBXTC"] = tc.values

    age = pd.to_numeric(j["RIDAGEYR"], errors="coerce").values
    flow, miss_tab = [], {}
    d0 = df
    flow.append(("all participants in DEMO", len(d0)))
    d1 = d0[age >= 20]
    flow.append(("1 aged 20 years or older", len(d1)))
    ridstatr = pd.to_numeric(j["RIDSTATR"], errors="coerce").values
    d2 = d1[ridstatr[d1.index] == 2]
    flow.append(("2 examined at the MEC (RIDSTATR = 2)", len(d2)))
    preg = pd.to_numeric(j["RIDEXPRG"], errors="coerce").values
    d3 = d2[preg[d2.index] != 1]
    flow.append(("3 not pregnant (RIDEXPRG != 1)", len(d3)))
    nolab = d3["HTN_L1_measured"].isna()
    flow.append(("   excluded: primary label L1 missing", int(nolab.sum())))
    flow.append(("      of which: no BPXO record or fewer than 2 readings for both SBP and DBP",
                 int((nolab & d3.SBP_mean.isna() & d3.DBP_mean.isna()).sum())))
    flow.append(("      of which: one of SBP/DBP below threshold, the other with fewer than 2 readings",
                 int((nolab & (d3.SBP_mean.notna() ^ d3.DBP_mean.notna())).sum())))
    d4 = d3[~nolab]
    flow.append(("4 primary label L1 available", len(d4)))
    miss = d4[FEATURES].isna()
    for f in FEATURES:
        flow.append((f"   missing {f}", int(miss[f].sum())))
        miss_tab[f] = {"n_missing": int(miss[f].sum()), "share_missing": trunc(float(miss[f].mean()))}
    miss_tab["_any_feature"] = {"n_missing": int(miss.any(axis=1).sum()), "share_missing": trunc(float(miss.any(axis=1).mean()))}
    d5 = d4[~miss.any(axis=1)].copy()
    flow.append(("5 complete cases on all features (analytic sample)", len(d5)))
    flow.append(("   L1 positive", int((d5.HTN_L1_measured == 1).sum())))
    flow.append(("   L1 negative", int((d5.HTN_L1_measured == 0).sum())))
    flow.append(("   L2 available", int(d5.HTN_L2_measured_or_treated.notna().sum())))
    flow.append(("   L2 positive", int((d5.HTN_L2_measured_or_treated == 1).sum())))
    flow.append(("   BPQ020 = 1 (told high BP; excluded from the less-exposed cohort)", int((d5.BPQ020_toldHighBP == 1).sum())))
    return d5, flow, miss_tab, base, j


def prevalence(d: pd.DataFrame) -> dict:
    l2 = d.HTN_L2_measured_or_treated
    le = d[d.BPQ020_toldHighBP != 1]
    return {"n": len(d),
            "L1_positive": int((d.HTN_L1_measured == 1).sum()), "L1_prevalence": trunc(float((d.HTN_L1_measured == 1).mean())),
            "L2_n_available": int(l2.notna().sum()), "L2_positive": int((l2 == 1).sum()),
            "L2_prevalence": trunc(float((l2[l2.notna()] == 1).mean())),
            "told_high_bp_n": int((d.BPQ020_toldHighBP == 1).sum()),
            "told_high_bp_share": trunc(float((d.BPQ020_toldHighBP == 1).mean())),
            "bp_med_now_n": int((d.BP_med_now == 1).sum()),
            "less_exposed_n": len(le), "less_exposed_L1_positive": int((le.HTN_L1_measured == 1).sum()),
            "less_exposed_L1_prevalence": trunc(float((le.HTN_L1_measured == 1).mean())),
            "KidneyDisease_1": int((d.KidneyDisease == 1).sum()), "Diabetes_1": int((d.Diabetes == 1).sum())}


def main():
    below_normal()
    check_prereg()
    DEST.mkdir(parents=True, exist_ok=True)
    gate, parts, flows, misses, cons = {}, [], {}, {}, {}
    for cycle in CYCLES:
        d5, flow, miss_tab, base, j = build(cycle, gate)
        parts.append(d5)
        flows[cycle], misses[cycle] = flow, miss_tab
        cons[cycle] = p7_consistency(cycle, base, j)
    pooled = pd.concat(parts, ignore_index=True)
    labels = ["HTN_L1_measured", "HTN_L2_measured_or_treated"]
    aux = ["Diabetes_borderline_as_yes", "BPQ020_toldHighBP", "BPQ080_toldHighChol", "BP_med_now", "WTMEC", "WTMEC_name",
           "SDMVPSU", "SDMVSTRA", "SBP_mean", "DBP_mean", "n_SBP_readings", "n_DBP_readings", "LBXTC"]
    pooled = pooled[["SEQN"] + labels + FEATURES + aux].sort_values(["Cycle", "SEQN"]).reset_index(drop=True)
    for c in ["HTN_L1_measured"] + FEATURES:
        pooled[c] = pooled[c].astype(int)
    pooled["HTN_L2_measured_or_treated"] = pooled["HTN_L2_measured_or_treated"].astype("Int64")
    out_csv = DEST / "nhanes_htn_analytic_2017-2023.csv"
    pooled.to_csv(out_csv, index=False, lineterminator="\n", float_format="%.6f")
    prev = {c: prevalence(pooled[pooled.Cycle == k]) for c, k in (("2017-2020", 0), ("2021-2023", 1))}
    prev["pooled"] = prevalence(pooled)

    lines = ["# NHANES hypertension analytic sample: flow (A0-HTN)", "",
             "Pooled NHANES 2017-2020 (P_ files) and 2021-2023 (_L files). Counts are participants. Shares are truncated "
             "to four decimals. L1 = measured (mean SBP >= 130 or mean DBP >= 80 mmHg, at least 2 readings each); "
             "L2 = L1 or now taking prescribed BP medication.", ""]
    for cycle, flow in flows.items():
        lines += [f"## {cycle}", "", "| Step | n |", "|---|---|"] + [f"| {s} | {k} |" for s, k in flow] + [""]
    lines += ["## Prevalence by cycle (analytic sample)", "",
              "| | 2017-2020 | 2021-2023 | pooled |", "|---|---|---|---|"]
    for key in prev["pooled"]:
        lines.append(f"| {key} | {prev['2017-2020'][key]} | {prev['2021-2023'][key]} | {prev['pooled'][key]} |")
    lines += ["", "## Missingness among label-available participants (step 4)", "",
              "| Feature | 2017-2020 n | 2017-2020 share | 2021-2023 n | 2021-2023 share |", "|---|---|---|---|---|"]
    for f in FEATURES + ["_any_feature"]:
        a, b = misses["2017-2020"][f], misses["2021-2023"][f]
        lines.append(f"| {f} | {a['n_missing']} | {a['share_missing']} | {b['n_missing']} | {b['share_missing']} |")
    (DEST / "nhanes_htn_flow.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    write_json(DEST / "nhanes_htn_flow.json", {"flow": flows, "prevalence": prev, "missingness_step4": misses,
                                               "pooled_n": len(pooled)})
    commit = subprocess.run(["git", "-C", str(NHANES_REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(NHANES_REPO), "status", "--short", "src"], capture_output=True, text=True).stdout.strip()
    write_json(DEST / "a0_gate_nhanes_htn.json", {"nhanes_diabetes_commit": commit, "nhanes_diabetes_src_uncommitted": dirty,
                                                   "gate": gate, "p7_feature_consistency_mismatches": cons,
                                                   "analytic_csv": str(out_csv), "analytic_csv_sha256": sha256_file(out_csv)})
    print("\n".join(lines))
    print("consistency", cons)


if __name__ == "__main__":
    main()
