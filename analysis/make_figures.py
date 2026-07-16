"""Generate Figure 1 (the knowledge graph) from the kg module.

Standalone: `python analysis/make_figures.py`
Also importable from a top-level runner.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D

from kg.edges import EDGES
from kg.nodes import TIER  # noqa: F401

BANDS = [("Lever", "lever", 3.0, "#2E7D32"),
         ("Treatable", "treatable", 2.0, "#1565C0"),
         ("Indicator", "indicator", 1.0, "#C62828"),
         ("Immutable / proxy", "immutable", 0.0, "#757575")]
ORDER = {
 "lever": ["BMI", "PhysActivity", "Fruits", "Veggies", "Smoker", "HvyAlcoholConsump", "NoDocbcCost"],
 "treatable": ["HighBP", "HighChol"],
 "indicator": ["GenHlth", "PhysHlth", "MentHlth", "DiffWalk"],
 "immutable": ["Age", "Sex", "Stroke", "HeartDiseaseorAttack", "Income", "Education", "AnyHealthcare", "CholCheck"],
}
STYLE = {"A": dict(ls="-", lw=1.9, alpha=0.85, color="#222222"),
         "B": dict(ls="--", lw=1.5, alpha=0.75, color="#444444"),
         "C": dict(ls=":", lw=1.5, alpha=0.70, color="#666666"),
         "-": dict(ls="-", lw=0.9, alpha=0.32, color="#999999")}


def make(out_dir: Path) -> None:
    pos = {}
    for _, tier, y, _ in BANDS:
        for i, n in enumerate(ORDER[tier]):
            pos[n] = ((i + 0.5) / len(ORDER[tier]) * 10, y)
    fig, ax = plt.subplots(figsize=(11, 6.2))
    for label, tier, y, col in BANDS:
        ax.add_patch(Rectangle((-0.55, y - 0.30), 11.2, 0.60, facecolor=col, alpha=0.055, edgecolor="none", zorder=0))
        ax.text(-0.75, y, label, ha="right", va="center", fontsize=10.5, weight="bold", color=col)
    seen = set()
    for e in EDGES:
        if e.src not in pos or e.dst not in pos or (e.src, e.dst, e.grade) in seen:
            continue
        seen.add((e.src, e.dst, e.grade))
        s, d, st = pos[e.src], pos[e.dst], STYLE[e.grade]
        ax.add_patch(FancyArrowPatch((s[0], s[1] - 0.16), (d[0], d[1] + 0.16), arrowstyle="-|>",
                     mutation_scale=11, connectionstyle=f"arc3,rad={0.14 if s[0] > d[0] else -0.14}",
                     linestyle=st["ls"], linewidth=st["lw"], alpha=st["alpha"], color=st["color"], zorder=1))
    for _, tier, y, col in BANDS:
        for n in ORDER[tier]:
            x, _y = pos[n]
            ax.text(x, _y, n, ha="center", va="center", fontsize=8.2, zorder=3,
                    bbox=dict(boxstyle="round,pad=0.30", facecolor="white", edgecolor=col, linewidth=1.25))
    ax.legend(handles=[Line2D([0], [0], color="#222222", ls="-", lw=1.9, label="ADA grade A"),
                       Line2D([0], [0], color="#444444", ls="--", lw=1.5, label="ADA grade B"),
                       Line2D([0], [0], color="#666666", ls=":", lw=1.5, label="ADA grade C"),
                       Line2D([0], [0], color="#999999", ls="-", lw=0.9, alpha=0.5, label="section narrative")],
              loc="lower right", fontsize=8.6, framealpha=0.95, ncol=4, bbox_to_anchor=(1.0, -0.10))
    ax.set_xlim(-2.6, 11.0); ax.set_ylim(-0.65, 3.55); ax.axis("off")
    ax.set_title("Every edge points down into the indicator band. None originate there.",
                 fontsize=10, style="italic", color="#444444", pad=8)
    plt.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_dir / "fig1_kg.pdf", bbox_inches="tight")
    plt.savefig(out_dir / "fig1_kg.png", dpi=300, bbox_inches="tight")
    print(f"Figure 1 -> {out_dir/'fig1_kg.pdf'}")


if __name__ == "__main__":
    make(Path(__file__).parent / "figures")
