"""Table S35 body from reclass_r5.json (v9 check against the printed table, then v10). Usage: s35_rows.py [v9]"""
import json
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")
O9 = "D:/20-study/uit/research/diabetesxai/paper7/outputs/"
GEN = {"dice_random": "DiCE random", "dice_genetic": "DiCE genetic", "exhaustive": "Exhaustive",
       "actionable_recourse_l1": "AR, range-scaled L1", "actionable_recourse_native": "AR, native cost",
       "growing_spheres": "Growing Spheres", "wachter": "Projected Wachter", "mint": "MINT-style"}
DS = {"brfss2021": "BRFSS 2021", "nhis2022": "NHIS 2022", "nhis2024": "NHIS 2024",
      "nhanes2017-2020_diag": "NHANES 2017–2020, diagnosis", "nhanes2017-2020_a1c": "NHANES 2017–2020, HbA1c",
      "nhanes2021-2023_diag": "NHANES 2021–2023, diagnosis", "nhanes2021-2023_a1c": "NHANES 2021–2023, HbA1c"}


def pc(x):
    return f"{math.trunc((float(x) * 10000) if GUARD == 0 else round(float(x) * 10000, 6)) / 100:.2f}%"


def model(c):
    if c.startswith("mlp_s"):
        return "MLP seed " + c[5:]
    return {"xgb": "XGB", "lr": "LR", "rf": "RF"}[c]


def rows(path):
    out = []
    for r in json.load(open(path, encoding="utf-8"))["rows"]:
        head = f"| {GEN[r['generator']]} | {model(r['classifier'])} | {DS[r['dataset']]} | {r['mode']} | {r.get('n_patients', 0)} |"
        if "touch" not in r:
            out.append(head + " – | – / – | – / – / – |")
            continue
        out.append(head + f" {pc(r['touch'])} | {pc(r['fully_v4'])} / {pc(r['fully_r5'])} | {pc(r['no_action_v4'])} / {pc(r['no_action_r5'])} / {pc(r['no_action_r5_7'])} |")
    return out


GUARD = 0 if (len(sys.argv) > 1 and sys.argv[1] == "v9") else 1
base = O9 if (len(sys.argv) > 1 and sys.argv[1] == "v9") else O9 + "p5_v10/outputs/"
print("\n".join(rows(base + "q1_posthoc_v5/reclass/reclass_r5.json")))
