"""Generate Figure 1 (the dependency graph) from the depgraph module.

Standalone: `python analysis/make_figures.py`
Also importable from a top-level runner.

The figure is drawn at the FULL TEXT WIDTH of the IEEE conference layout
(6.77 in on A4 with 1.9 cm margins), so the font sizes below are the sizes the
reader actually sees in print. Do not rescale the image when placing it.

One arrow is drawn per distinct source-target pair, at the strongest evidence
grade asserting that pair. K_G has 26 edges over 21 distinct pairs; five pairs
are asserted twice by different recommendations, and drawing both would put two
overlapping arrows on the same path.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import matplotlib
matplotlib.use("Agg")
# TrueType, not Type 3: IEEE PDF eXpress rejects Type 3 fonts.
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D

from depgraph.edges import EDGES
from depgraph.nodes import TIER  # noqa: F401

# ---------------------------------------------------------------- print geometry
FIG_W_IN = 6.77        # full text width, A4 with 1.9 cm margins
FIG_H_IN = 3.45
FS_NODE = 6.6          # >= 6 pt, IEEE floor for figure text
FS_BAND = 8.0
FS_LEGEND = 7.0

BANDS = [("Lever", "lever", 3.0, "#2E7D32"),
         ("Treatable", "treatable", 2.0, "#1565C0"),
         ("Indicator", "indicator", 1.0, "#C62828"),
         ("Immutable /\nproxy", "immutable", 0.0, "#757575")]
ORDER = {
 "lever": ["Fruits", "Veggies", "PhysActivity", "BMI", "Smoker", "HvyAlcoholConsump", "NoDocbcCost"],
 "treatable": ["HighBP", "HighChol"],
 "indicator": ["GenHlth", "PhysHlth", "MentHlth", "DiffWalk"],
 "immutable": ["Age", "Sex", "Stroke", "HeartDiseaseorAttack", "Income", "Education", "AnyHealthcare", "CholCheck"],
}
# Two-line labels keep the long BRFSS names legible at 6.6 pt.
WRAP = {"HvyAlcoholConsump": "HvyAlcohol\nConsump",
        "NoDocbcCost": "NoDocbc\nCost",
        "HeartDiseaseorAttack": "HeartDisease\norAttack",
        "PhysActivity": "PhysActivity",
        "AnyHealthcare": "AnyHealthcare"}

STYLE = {"A": dict(ls="-", lw=1.25, alpha=0.90, color="#1A1A1A"),
         "B": dict(ls=(0, (4.5, 2.0)), lw=1.05, alpha=0.85, color="#3C3C3C"),
         "C": dict(ls=(0, (1.2, 1.6)), lw=1.05, alpha=0.85, color="#5A5A5A"),
         "-": dict(ls="-", lw=0.65, alpha=0.45, color="#9E9E9E")}
RANK = {"A": 0, "B": 1, "C": 2, "E": 3, "-": 4}

# half-width of a node box, in data units, per band
HALF = {"lever": 0.42, "treatable": 0.42, "indicator": 0.42, "immutable": 0.42}
NODE_H = 0.115         # half-height of a node box, data units


def strongest_pairs():
    """One (src, dst) -> grade mapping, keeping the strongest grade per pair."""
    best = {}
    for e in EDGES:
        key = (e.src, e.dst)
        if key not in best or RANK[e.grade] < RANK[best[key]]:
            best[key] = e.grade
    return best


def make(out_dir: Path) -> None:
    pos = {}
    for _, tier, y, _ in BANDS:
        n = len(ORDER[tier])
        for i, name in enumerate(ORDER[tier]):
            pos[name] = ((i + 0.5) / n * 10.0, y)

    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN))

    for label, tier, y, col in BANDS:
        ax.add_patch(Rectangle((-0.30, y - 0.235), 10.60, 0.47, facecolor=col,
                               alpha=0.06, edgecolor="none", zorder=0))
        ax.text(-0.50, y, label, ha="right", va="center", fontsize=FS_BAND,
                weight="bold", color=col, linespacing=1.05)

    pairs = strongest_pairs()
    # Fan the arrival points across the target node so converging edges stay
    # distinguishable instead of collapsing into a single blob.
    incoming = {}
    for (s, d) in pairs:
        incoming.setdefault(d, []).append(s)
    for d in incoming:
        incoming[d].sort(key=lambda s: pos[s][0])

    for (s_name, d_name), grade in sorted(pairs.items(), key=lambda kv: RANK[kv[1]], reverse=True):
        st = STYLE[grade]
        sx, sy = pos[s_name]
        dx, dy = pos[d_name]
        sibs = incoming[d_name]
        k = sibs.index(s_name)
        spread = 0.62 * HALF[TIER[d_name]]
        off = 0.0 if len(sibs) == 1 else (k / (len(sibs) - 1) - 0.5) * 2 * spread
        ax.add_patch(FancyArrowPatch(
            (sx, sy - NODE_H - 0.015), (dx + off, dy + NODE_H + 0.015),
            arrowstyle="-|>", mutation_scale=6.5, shrinkA=0, shrinkB=0,
            connectionstyle=f"arc3,rad={0.10 if sx > dx else -0.10}",
            linestyle=st["ls"], linewidth=st["lw"], alpha=st["alpha"],
            color=st["color"], zorder=1))

    for _, tier, y, col in BANDS:
        for name in ORDER[tier]:
            x, yy = pos[name]
            ax.text(x, yy, WRAP.get(name, name), ha="center", va="center",
                    fontsize=FS_NODE, linespacing=0.95, zorder=3,
                    bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                              edgecolor=col, linewidth=0.75))

    ax.legend(handles=[Line2D([0], [0], **{k: v for k, v in STYLE["A"].items() if k != "alpha"}, label="ADA grade A"),
                       Line2D([0], [0], **{k: v for k, v in STYLE["B"].items() if k != "alpha"}, label="ADA grade B"),
                       Line2D([0], [0], **{k: v for k, v in STYLE["C"].items() if k != "alpha"}, label="ADA grade C"),
                       Line2D([0], [0], color="#9E9E9E", ls="-", lw=0.65, label="section narrative")],
              loc="lower center", fontsize=FS_LEGEND, framealpha=0.0, ncol=4,
              handlelength=2.6, columnspacing=1.6, borderpad=0.1,
              bbox_to_anchor=(0.46, -0.055))

    ax.set_xlim(-2.10, 10.35)
    ax.set_ylim(-0.55, 3.32)
    ax.axis("off")
    plt.subplots_adjust(left=0.005, right=0.998, top=0.995, bottom=0.055)
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_dir / "fig1_kg.pdf")
    plt.savefig(out_dir / "fig1_kg.png", dpi=600)
    print(f"Figure 1 -> {out_dir/'fig1_kg.pdf'}  ({FIG_W_IN} x {FIG_H_IN} in, node text {FS_NODE} pt)")


if __name__ == "__main__":
    make(Path(__file__).parent / "figures")
