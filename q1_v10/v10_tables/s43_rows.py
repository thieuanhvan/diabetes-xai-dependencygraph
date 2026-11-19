"""Table S43 rows (v10) from matched_three_disease.json, formatted as in supplement v7; n/prevalence from collect_v10."""
import json
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")
O = "D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/"
d = json.load(open(O + "outputs/q1_posthoc_v5/analysis/matched_three_disease.json", encoding="utf-8"))
c = json.load(open(O + "collect_v10.json", encoding="utf-8"))["v10"]


def tr(x, k=4):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


def f(x):
    return f"{tr(x):.4f}".replace("-", "−")


def p(x):
    return f"{tr(x * 100, 2):.2f}%"


def n(x):
    return f"{int(x):,}"


ROWS = [("Diabetes, HbA1c ≥ 6.5%", "diabetes_a1c", c["dm_a1c"]), ("Diabetes, diagnosis label (refit)", "diabetes_diag", c["dm_diag"]),
        ("Diabetes, HbA1c, HighBP measured as in CKD (refit)", "diabetes_hbp_measured", c["dm_hbp_measured"]),
        ("CKD (S-P1)", "ckd_ses_freeze", c["table2_ckd"]), ("Hypertension", "htn_main", c["table2_htn"])]
for name, k, t in ROWS:
    r = d[k]
    pub, lock = r["dice"]["published"], r["dice"]["lock"]
    na = r["no_action"]
    a3 = r["O_A3"]
    cov = f(r["coverage"]["lock"]["share"])
    print(f"| {name} | {n(t['n'])}; {p(t['prevalence'])} | {f(r['test_auc'])} | {r['eligible']}; {r['n_cohort']} | "
          f"{f(r['single_nonindicator_flip_share'])} | {p(pub['touch_patient_mean'])} | {p(na['est'])} [{p(na['ci95'][0])}, {p(na['ci95'][1])}] | "
          f"{f(r['O_A2']['T'])} vs {f(r['O_A2']['null_mean'])}; {f(r['O_A2']['p'])} | {f(a3['est'])} [{f(a3['lower_one_sided_99'])}]; {cov} | "
          f"{p(pub['bmi_patient_mean'])} / {p(lock['bmi_patient_mean'])} |")
