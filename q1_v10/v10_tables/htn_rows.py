"""htn_rows.py <a2_analysis dir>: rows of Supplementary Tables S45 and S34 (hypertension variants) from
results_<variant>.json, truncated. Run on the v9 folder to confirm it reproduces the printed v9 tables."""
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
D = Path(sys.argv[1])
V = [("main", "Main, measured label"), ("less_exposed", "Excluding told of high blood pressure"),
     ("rimm_off", "Socio-economic features movable"), ("l2", "Label: measured or treated, refit"),
     ("no_bpmed", "Without current medication users, refit"), ("no_dx", "Without diagnosis histories, refit")]
S34 = {"main": "Main", "less_exposed": "Excluding told of high blood pressure", "rimm_off": "Socio-economic features movable",
       "l2": "Measured or treated, refit", "no_bpmed": "Without current medication users, refit",
       "no_dx": "Without diagnosis histories, refit"}


def f4(x):
    return f"{math.trunc(round(x * 10000, 6)) / 10000:.4f}".replace("-", "−")


def vd(s):
    return {"supported": "S", "not supported": "N", "undecided": "U"}[s]


a, b, missing = [], [], []
for v, nm in V:
    f = D / f"results_{v}.json"
    if not f.exists():
        missing.append(v)
        continue
    j = json.load(open(f, encoding="utf-8"))
    o1, o2, o3 = j["O_A1_fully_unactionable_dice_published"], j["O_A2_movability_null"], j["O_A3_valid_among_requested_lock_minus_published"]
    a.append(f"| {nm} | {f4(j['test_auc'])} | {f4(o1['est'])} [{f4(o1['lower_one_sided_99'])}, {f4(o1['upper_one_sided_99'])}] | "
             f"{f4(o2['T_mean_oshare'])} vs {f4(o2['null_mean_of_means'])}; {f4(o2['p'])} | {f4(o3['est'])} [{f4(o3['lower_one_sided_99'])}]; "
             f"{f4(j['coverage_dice']['lock']['share'])} | {vd(j['H1']['verdict'])}, {vd(j['H2']['verdict'])} |")
    t, lk = j["touch_share_dice_published"], j["leakage_published_other_authorities"]["dice_random"]
    ex = j["exhaustive_costs"]["lock"]["dist_minus_published"]
    b.append(f"| {S34[v]} | {f4(j['S1_single_nonindicator_flip']['share'])} | {f4(t['est'])} [{f4(t['ci95'][0])}, {f4(t['ci95'][1])}] | "
             f"{f4(o3['published_valid_among_requested'])} / {f4(o3['lock_valid_among_requested'])} | {f4(lk['kdigo_k1']['est'])}; {f4(lk['ada_k1']['est'])} | "
             f"{f4(ex['est'])} [{f4(ex['ci95'][0])}, {f4(ex['ci95'][1])}] |")
    if v == "main":
        pc = j["per_cycle_dice_published"]
        fc = j["feature_change_counts_dice_published"]
        info = (f"per cycle O_A1 {f4(pc['2017-2020']['O_A1']['est'])} / {f4(pc['2021-2023']['O_A1']['est'])}; feature changes {fc}; "
                f"cohort n {o1['n']} without cf {o1.get('patients_without_cf')}")
    if v == "rimm_off":
        info_r = f"rimm_off feature changes {j['feature_change_counts_dice_published']}"
print("S45")
print("\n".join(a))
print("S34")
print("\n".join(b))
print("INFO", info)
if "rimm_off" not in missing:
    print("INFO", info_r)
print("MISSING", missing)
