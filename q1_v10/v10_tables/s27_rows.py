"""Table S27 rows from ses_shares_and_runs.json (v9 check of the CKD row, then v10), plus the ext_b shares."""
import json
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")
B = "D:/20-study/uit/research/diabetesxai/paper7/outputs/"


def tr(x, k=2):
    return math.trunc(round(float(x) * 10 ** k, 6)) / 10 ** k


def p(x):
    return f"{tr(float(x) * 100):.2f}%"


def rows(path):
    d = json.load(open(path, encoding="utf-8"))
    c = d["ckd_a2_main"]
    out = [f"| CKD (main cohort, KDIGO) | " + " | ".join(f"{p(c[f'dice_{m}_all']['ses_touch'])} / {p(c[f'dice_{m}_all']['ses_only'])}" for m in ("published", "lock", "route"))
           + f" | {p(c['exh_published_best']['ses_only'])} | {p(c['exh_lock_best']['ses_only'])} |"]
    for nm in ("BRFSS 2021", "NHIS 2022", "NHIS 2024", "NHANES 2017-2020 diagnosis", "NHANES 2017-2020 HbA1c",
               "NHANES 2021-2023 diagnosis", "NHANES 2021-2023 HbA1c"):
        g = lambda gen, m, w: d["diabetes"][f"{nm}|{gen}|{m}|{w}"]  # noqa: E731
        label = nm.replace("2017-2020 ", "2017–2020, ").replace("2021-2023 ", "2021–2023, ")
        out.append(f"| {label} | " + " | ".join(f"{p(g('dice', m, 'all')['ses_touch'])} / {p(g('dice', m, 'all')['ses_only'])}" for m in ("published", "lock", "route"))
                   + f" | {p(g('exh', 'published', 'best')['ses_only'])} | {p(g('exh', 'lock', 'best')['ses_only'])} |")
    return out, d


v9, _ = rows(B + "q1_posthoc_ses_splits/ses_shares_and_runs.json")
assert v9[0] == "| CKD (main cohort, KDIGO) | 35.19% / 9.27% | 46.42% / 12.68% | 35.29% / 12.90% | 13.82% | 17.74% |", v9[0]
assert v9[1] == "| BRFSS 2021 | 15.78% / 2.74% | 22.02% / 4.06% | 16.66% / 3.40% | 18.00% | 21.50% |", v9[1]
v10, d = rows(B + "p5_v10/outputs/q1_posthoc_ses_splits/ses_shares_and_runs.json")
print("\n".join(v10))
print({k: {m: v for m, v in x.items()} for k, x in d.get("ext_b", {}).items() if "published" in k})
print([k for k in d["diabetes"] if "cholcheck" in json.dumps(d["diabetes"][k])][:3])
