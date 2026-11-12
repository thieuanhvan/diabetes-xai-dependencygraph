"""Figure 5 (post hoc S-P5): no-action share of DiCE random counterfactuals in the three diseases on matched NHANES
data, published mode (95% patient bootstrap interval) and indicator lock. Reads matched_three_disease.json only.
Usage (P4 venv, has matplotlib): python -I v5_fig5_three_disease.py
Output: outputs/journal_main/figures_v3/fig5_three_disease.{png,pdf,eps}
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

O = Path("D:/20-study/uit/research/diabetesxai/paper7/outputs")
R = json.loads((O / "q1_posthoc_v5" / "analysis" / "matched_three_disease.json").read_text(encoding="utf-8"))
ROWS = [("Diabetes\n(HbA1c)", "diabetes_a1c"), ("Diabetes\n(diagnosis)", "diabetes_diag"),
        ("CKD", "ckd_ses_freeze"), ("Hypertension", "htn_main")]


def main():
    lab, pub, lo, hi, lock = [], [], [], [], []
    for name, key in ROWS:
        r = R[key]
        lab.append(name)
        pub.append(100 * r["no_action"]["est"])
        lo.append(100 * (r["no_action"]["est"] - r["no_action"]["ci95"][0]))
        hi.append(100 * (r["no_action"]["ci95"][1] - r["no_action"]["est"]))
        lock.append(100 * r["dice"]["lock"]["no_action_patient_mean"])
    x = range(len(lab))
    fig, ax = plt.subplots(figsize=(6.2, 3.4), dpi=150)
    ax.bar([i - 0.19 for i in x], pub, 0.38, yerr=[lo, hi], capsize=3, color="#4c72b0", label="Published mode")
    ax.bar([i + 0.19 for i in x], lock, 0.38, color="#c4c4c4", edgecolor="#555555", label="Indicator lock")
    ax.set_xticks(list(x))
    ax.set_xticklabels(lab, fontsize=9)
    ax.set_ylabel("Counterfactuals with no action (%)", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    out = O / "journal_main" / "figures_v3"
    fig.savefig(out / "fig5_three_disease.png", dpi=1000)
    fig.savefig(out / "fig5_three_disease.pdf")
    fig.savefig(out / "fig5_three_disease.eps")
    print("written", out / "fig5_three_disease.png")


if __name__ == "__main__":
    main()
