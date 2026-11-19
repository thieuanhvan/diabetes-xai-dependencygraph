"""s26_other_sets.py <recount_s_p6.csv>: largest difference (percentage points, truncated) between valid-only and
all-returned shares for the 'other output sets' of Supplementary Section S26 (diabetes surveys: logistic regression and
random forest with DiCE random, DiCE genetic, exhaustive search), per metric group. Run on v9 first to find the
definition of the printed 3.87, then on v10."""
import math
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
d = pd.read_csv(sys.argv[1])
d = d[d.domain == "diabetes_survey"]
other = d[((d.generator == "dice_random") & d.classifier.isin(["lr", "rf"])) |
          d.generator.isin(["dice_genetic", "exhaustive"])]
k = ["generator", "classifier", "dataset", "mode"]
a = other[other.denominator == "all"].set_index(k)
v = other[other.denominator == "valid"].set_index(k)
groups = {"no_action all readings": ["no_action_v4", "no_action_r5", "no_action_r6", "no_action_nb_r5", "no_action_nb_r6"],
          "no_action v4/r5/r6/nb_r5": ["no_action_v4", "no_action_r5", "no_action_r6", "no_action_nb_r5"],
          "no_action + fully all": [c for c in d.columns if c.startswith(("no_action_", "fully_")) and c not in
                                    ("no_action_graph", "fully_graph", "no_action_nb", "fully_nb")],
          "touch": ["touch"]}


def tr(x):
    return math.trunc(round(x * 10000, 6)) / 100


for g, cols in groups.items():
    diff = (v[cols] - a.loc[v.index, cols]).abs()
    by_gen = diff.max(axis=1).groupby(level=0).max()
    print(f"{g}: max {tr(diff.max().max()):.2f} pp; by generator " +
          ", ".join(f"{x} {tr(y):.2f}" for x, y in by_gen.items()))
print("rows other sets:", len(v), "modes:", sorted(set(v.index.get_level_values("mode"))))
