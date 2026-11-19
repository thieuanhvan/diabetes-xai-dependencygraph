"""gain_bmi.py: share of total XGBoost gain on BMI for the hypertension and CKD models, v9 and v10 (reads model files)."""
import sys

import xgboost as xgb

sys.stdout.reconfigure(encoding="utf-8")
B = "D:/20-study/uit/research/diabetesxai/paper7/outputs/"
for v, base in (("v9", B), ("v10", B + "p5_v10/outputs/")):
    for dom, f in (("htn", "q1_domain_htn/a2_model/xgb_htn.json"), ("ckd", "q1_domain_ckd/a2_model/xgb_ckd.json")):
        bst = xgb.Booster()
        bst.load_model(base + f)
        g = bst.get_score(importance_type="total_gain")
        tot = sum(g.values())
        print(v, dom, "BMI total_gain share", g.get("BMI", 0) / tot)
        g = bst.get_score(importance_type="gain")
        print(v, dom, "BMI gain share", g.get("BMI", 0) / sum(g.values()))
