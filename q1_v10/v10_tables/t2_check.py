"""Table 2 NHANES diabetes rows (n, prevalence per label) for v9 inputs and v10 P5 frames."""
import pandas as pd
V9 = "C:/Repos/uit/nhanes-diabetes/outputs/tabular/cdc_nhanes_diabetes_{c}.csv"
V10 = "D:/20-study/uit/research/diabetesxai/paper7/outputs/p5_v10/frames/t4_{c}_p5.csv"
for c in ("2017-2020", "2021-2023"):
    for tag, p in (("v9", V9), ("v10", V10)):
        d = pd.read_csv(p.format(c=c))
        labs = [x for x in d.columns if "diab" in x.lower() or "a1c" in x.lower() or "label" in x.lower()]
        print(tag, c, len(d), {l: (int(d[l].notna().sum()), float(d[l].mean())) for l in labs})
for c in ("2017-2020", "2021-2023"):
    d = pd.read_csv(V10.format(c=c))
    print("v10", c, len(d), "diag", float(d.Diabetes_self.mean()), "a1c", float((d.HbA1c >= 6.5).mean()))
