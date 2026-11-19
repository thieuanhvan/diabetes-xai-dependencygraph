"""s47_rows.py <recount_s_p6.json>: rows of Supplementary Table S47 (S-P6 recount), truncated, plus checks for the
caption and the S26 reading prose. Run on the v9 json to confirm it reproduces the printed v9 table."""
import json
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")
j = json.load(open(sys.argv[1], encoding="utf-8"))
R = {}
for r in j["rows"]:
    R[(r["domain"], r["generator"], r["classifier"], r["dataset"], r["mode"], r["denominator"])] = r


def p(x):
    return f"{math.trunc(round(x * 10000, 6)) / 100:.2f}"


def ci(r, k):
    c = r.get("ci95_" + k)
    return f" [{p(c[0])}, {p(c[1])}]" if c else ""


NAME = {"brfss2021": "BRFSS 2021", "nhis2022": "NHIS 2022", "nhis2024": "NHIS 2024",
        "nhanes2017-2020_diag": "NHANES 2017–2020, diagnosis", "nhanes2017-2020_a1c": "NHANES 2017–2020, HbA1c",
        "nhanes2021-2023_diag": "NHANES 2021–2023, diagnosis", "nhanes2021-2023_a1c": "NHANES 2021–2023, HbA1c"}
out = []
for ds, nm in NAME.items():
    a = R[("diabetes_survey", "dice_random", "xgb", ds, "published", "all")]
    v = R[("diabetes_survey", "dice_random", "xgb", ds, "published", "valid")]
    out.append(f"| {nm} | {a['n_patients']} | {p(a['no_action_v4'])} / {p(v['no_action_v4'])} | {p(a['no_action_r5'])}{ci(a, 'no_action_r5')} | "
               f"{p(v['no_action_r5'])}{ci(v, 'no_action_r5')} | {p(a['no_action_r6'])} | {p(a['no_action_nb_r5'])} / {p(v['no_action_nb_r5'])} |")


def g(dom, den):
    return R[(dom, "dice_random", "xgb", "nhanes_2017-2023", "published", den)]


for dom, nm, withci in (("ckd_main", "CKD main, pre-specified", True), ("ckd_ses_freeze", "CKD, socio-economic features frozen (S-P1)", True)):
    a, v = g(dom, "all"), g(dom, "valid")
    out.append(f"| {nm} | {a['n_patients']} | {p(a['no_action_graph'])}{ci(a, 'no_action_graph')} / {p(v['no_action_graph'])}{ci(v, 'no_action_graph')} | – | – | – | "
               f"{p(a['no_action_nb'])} / {p(v['no_action_nb'])} |")
sp = [f"ckd_split_{s}" for s in (11, 22, 33, 44, 55)]


def rng(k, den):
    xs = [g(d, den)[k] for d in sp]
    return f"{p(min(xs))}–{p(max(xs))}"


ns = [g(d, "all")["n_patients"] for d in sp]
out.append(f"| CKD, five further splits (S-P2) | {min(ns)}–{max(ns)} | {rng('no_action_graph', 'all')} / {rng('no_action_graph', 'valid')} | – | – | – | "
           f"{rng('no_action_nb', 'all')} / {rng('no_action_nb', 'valid')} |")
for dom, nm, withci in (("htn_main", "Hypertension main", True), ("matched_dm_a1c", "Matched diabetes, HbA1c label", True),
                        ("matched_dm_diag", "Matched diabetes, diagnosis label", False)):
    a, v = g(dom, "all"), g(dom, "valid")
    c1 = ci(a, "no_action_graph") if withci else ""
    c2 = ci(v, "no_action_graph") if withci else ""
    out.append(f"| {nm} | {a['n_patients']} | {p(a['no_action_graph'])}{c1} / {p(v['no_action_graph'])}{c2} | – | – | – | "
               f"{p(a['no_action_nb'])} / {p(v['no_action_nb'])} |")
print("\n".join(out))
print("\nCHECKS")
diff = [(k[0], k[1], k[2], k[3], k[4]) for k, r in R.items() if k[5] == "all" and
        (k[:5] + ("valid",)) in R and R[k[:5] + ("valid",)]["n_patients"] != r["n_patients"]]
print("patients differ all vs valid:", [(d, R[d + ("all",)]["n_patients"], R[d + ("valid",)]["n_patients"]) for d in diff])
md = 0
for k, r in R.items():
    if k[5] == "all" and k[0] == "diabetes_survey" and k[:2] != ("diabetes_survey", "dice_random") or (k[5] == "all" and k[0] == "diabetes_survey" and k[2] != "xgb"):
        v = R.get(k[:5] + ("valid",))
        if v:
            for m in ("no_action_r5", "no_action_v4", "fully_r5", "fully_v4"):
                md = max(md, abs(v[m] - r[m]))
print("max |valid - all| other diabetes sets (pp):", p(md))
ex = max(abs(R[k[:5] + ("valid",)][m] - r[m]) for k, r in R.items() if k[1] == "exhaustive" and k[5] == "all"
         for m in ("no_action_r5", "no_action_v4"))
print("exhaustive max diff:", p(ex))
dm = [R[("diabetes_survey", "dice_random", "xgb", ds, "published", "all")] for ds in NAME]
dv = [R[("diabetes_survey", "dice_random", "xgb", ds, "published", "valid")] for ds in NAME]
print("R5 valid - all (pp):", {ds: p(v["no_action_r5"] - a["no_action_r5"]) if v["no_action_r5"] >= a["no_action_r5"] else "-" + p(a["no_action_r5"] - v["no_action_r5"]) for ds, a, v in zip(NAME, dm, dv)})
print("R6 - R5 (pp):", p(min(a["no_action_r6"] - a["no_action_r5"] for a in dm)), p(max(a["no_action_r6"] - a["no_action_r5"] for a in dm)))
print("NB-R5 range all:", p(min(a["no_action_nb_r5"] for a in dm)), p(max(a["no_action_nb_r5"] for a in dm)))
print("R5 valid range:", p(min(v["no_action_r5"] for v in dv)), p(max(v["no_action_r5"] for v in dv)))
print("forced:", j["forced_lever_networks_46_48_49"])
