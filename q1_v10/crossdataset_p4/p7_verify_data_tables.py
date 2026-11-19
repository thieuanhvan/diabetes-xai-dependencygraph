"""Pre-submission check: Table 1 (n, prevalence) and Table S3 (AUC, cohort, eligible) from the data loaders and
locked result summaries. Prints values truncated as in the manuscript."""
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p7_cross_p4pipeline as P  # noqa: E402

R = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\p5_v10\outputs\crossdataset_p4") / "results"


def tr(x, k):
    return math.trunc(round(x * 10 ** k, 6)) / 10 ** k


for ds in ["brfss2021", "nhis2022", "nhis2024", "nhanes2017-2020_diag", "nhanes2017-2020_a1c",
           "nhanes2021-2023_diag", "nhanes2021-2023_a1c"]:
    X, y, _ = P.load(ds)
    print(f"{ds:22s} n={len(y):,} prev={tr(y.mean() * 100, 2):.2f}% nfeat={X.shape[1]} cols={','.join(X.columns)}")
for tag in ["_v2", "_v3", "_gen2", "_exh", ""]:
    for f in sorted(R.glob(f"cross_*{tag}_summary.csv")):
        nm = f.name[len("cross_"):-len(f"{tag}_summary.csv")]
        if any(t in nm for t in ("_v2", "_v3", "_gen", "_exh", "_mh", "_nosmk", "bmi4")) and tag == "":
            continue
        s = pd.read_csv(f)
        print(f"{tag or 'v1':5s} {nm:24s} auc={sorted(set(s.auc))} cohort={sorted(set(s.cohort))} eligible={sorted(set(s.eligible))}")
