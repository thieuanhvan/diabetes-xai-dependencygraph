"""Generate Figure 1 (the dependency graph) from the depgraph module.

Standalone: `python analysis/make_figures.py`
Also importable from a top-level runner.

The figure is drawn at the FULL TEXT WIDTH of the IEEE conference layout
(6.77 in on A4), so the font sizes below are the sizes the reader actually sees
in print. Do not rescale the image when placing it.

One arrow is drawn per distinct source-target pair, at the strongest evidence
grade asserting that pair. K_G has 26 edges over 21 distinct pairs; five pairs
are asserted twice by different recommendations, and drawing both would put two
overlapping arrows on the same path.

Structural invariants the figure encodes (kept true by construction, do not break):
  - four role bands, top to bottom: lever / treatable / indicator / immutable
  - line style encodes the ADA evidence grade (A solid, B dashed, C dotted,
    section narrative = faint thin warm line)
  - no edge originates in the indicator band (indicators are sinks)
  - the immutable band is disconnected (lies on no route)
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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.lines import Line2D

from depgraph.edges import EDGES
from depgraph.nodes import TIER  # noqa: F401

# ---------------------------------------------------------------- print geometry
FIG_W_IN = 6.77        # full text width, A4
FIG_H_IN = 3.60
FS_NODE = 6.6          # >= 6 pt, IEEE floor for figure text
FS_BAND = 8.5
FS_LEGEND = 7.0
FS_NOTE = 6.8
NODE_H = 0.125
HUB = {"BMI"}          # visually emphasise the hub

# band label, tier key, y, dark colour, light fill
BANDS = [("LEVER",             "lever",     3.00, "#1B5E20", "#E7F1E8"),
         ("TREATABLE",         "treatable", 2.00, "#0D47A1", "#E6EEF7"),
         ("INDICATOR",         "indicator", 1.00, "#B71C1C", "#FBE9E9"),
         ("IMMUTABLE / proxy", "immutable", -0.20, "#616161", "#EFEFEF")]

ORDER = {
    "lever": ["Fruits", "Veggies", "PhysActivity", "BMI", "Smoker",
              "HvyAlcoholConsump", "NoDocbcCost"],
    "treatable": ["HighBP", "HighChol"],
    "indicator": ["GenHlth", "PhysHlth", "MentHlth", "DiffWalk"],
    "immutable": ["Age", "Sex", "Stroke", "HeartDiseaseorAttack", "Income",
                  "Education", "AnyHealthcare", "CholCheck"],
}
WRAP = {"HvyAlcoholConsump": "HvyAlcohol\nConsump",
        "NoDocbcCost": "NoDocbc\nCost",
        "HeartDiseaseorAttack": "HeartDisease\norAttack"}

# grade -> line style; weight/alpha reinforce, narrative is the faint warm line
STYLE = {"A": dict(ls="-",           lw=1.35, alpha=0.92, color="#20303A"),
         "B": dict(ls=(0, (4.5, 2.0)), lw=1.10, alpha=0.88, color="#30465A"),
         "C": dict(ls=(0, (1.1, 1.7)), lw=1.10, alpha=0.88, color="#4A6274"),
         "-": dict(ls="-",           lw=0.70, alpha=0.55, color="#C08A2E")}
RANK = {"A": 0, "B": 1, "C": 2, "E": 3, "-": 4}


def _strongest_pairs():
    """26 edges -> 21 arrows: keep the strongest grade per (src, dst)."""
    best = {}
    for e in EDGES:
        k = (e.src, e.dst)
        if k not in best or RANK[e.grade] < RANK[best[k]]:
            best[k] = e.grade
    return best


def make(out_dir: Path):
    pos = {}
    for _, tier, y, _, _ in BANDS:
        n = len(ORDER[tier])
        for i, name in enumerate(ORDER[tier]):
            pos[name] = ((i + 0.5) / n * 10.0, y)

    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN))

    # band backgrounds; indicator band emphasised (it is the focus)
    for label, tier, y, dark, fill in BANDS:
        emph = 0.55 if tier == "indicator" else 0.42
        ax.add_patch(plt.Rectangle((-0.35, y - 0.27), 10.70, 0.54, facecolor=fill,
                                   edgecolor="none", zorder=0, alpha=emph))
        ax.text(-0.62, y, label, ha="right", va="center", fontsize=FS_BAND,
                weight="bold", color=dark, linespacing=1.0)

    # disconnection cue between indicator and immutable
    ax.axhline(0.40, xmin=0.03, xmax=0.985, color="#BDBDBD", lw=0.6,
               ls=(0, (2, 3)), zorder=0)
    ax.text(10.32, 0.40, "no edges cross", ha="right", va="bottom",
            fontsize=FS_NOTE - 0.6, style="italic", color="#9E9E9E", zorder=0)

    pairs = _strongest_pairs()
    incoming = {}
    for (s, d) in pairs:
        incoming.setdefault(d, []).append(s)
    for d in incoming:
        incoming[d].sort(key=lambda s: pos[s][0])

    # draw weakest first so graded edges sit on top
    for (s, d), g in sorted(pairs.items(), key=lambda kv: RANK[kv[1]], reverse=True):
        st = STYLE[g]
        sx, sy = pos[s]
        dx, dy = pos[d]
        sibs = incoming[d]
        k = sibs.index(s)
        spread = 0.26
        off = 0.0 if len(sibs) == 1 else (k / (len(sibs) - 1) - 0.5) * 2 * spread
        ax.add_patch(FancyArrowPatch(
            (sx, sy - NODE_H - 0.012), (dx + off, dy + NODE_H + 0.012),
            arrowstyle="-|>", mutation_scale=6.8, shrinkA=0, shrinkB=0,
            connectionstyle=f"arc3,rad={0.11 if sx > dx else -0.11}",
            linestyle=st["ls"], linewidth=st["lw"], alpha=st["alpha"],
            color=st["color"], zorder=1, capstyle="round"))

    # nodes (hub filled + bold + thicker border)
    for _, tier, y, dark, fill in BANDS:
        for name in ORDER[tier]:
            x, yy = pos[name]
            is_hub = name in HUB
            ax.add_patch(FancyBboxPatch(
                (x - 0.44, yy - NODE_H), 0.88, 2 * NODE_H,
                boxstyle="round,pad=0.018,rounding_size=0.06",
                facecolor=fill if is_hub else "white",
                edgecolor=dark, linewidth=1.5 if is_hub else 0.8,
                zorder=3, mutation_aspect=0.5))
            ax.text(x, yy, WRAP.get(name, name), ha="center", va="center",
                    fontsize=FS_NODE, linespacing=0.92, zorder=4,
                    weight="bold" if is_hub else "normal", color="#111")

    ax.legend(handles=[
        Line2D([0], [0], color=STYLE["A"]["color"], ls="-", lw=1.35, label="ADA grade A"),
        Line2D([0], [0], color=STYLE["B"]["color"], ls=(0, (4.5, 2.0)), lw=1.10, label="ADA grade B"),
        Line2D([0], [0], color=STYLE["C"]["color"], ls=(0, (1.1, 1.7)), lw=1.10, label="ADA grade C"),
        Line2D([0], [0], color=STYLE["-"]["color"], ls="-", lw=0.9, label="section narrative")],
        loc="lower center", fontsize=FS_LEGEND, framealpha=0.0, ncol=4,
        handlelength=2.5, columnspacing=1.5, borderpad=0.1,
        bbox_to_anchor=(0.47, -0.075))

    ax.set_xlim(-2.35, 10.55)
    ax.set_ylim(-0.62, 3.34)
    ax.axis("off")
    plt.subplots_adjust(left=0.004, right=0.999, top=0.996, bottom=0.06)
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_dir / "fig1_kg.pdf")
    plt.savefig(out_dir / "fig1_kg.png", dpi=600)
    print(f"Figure 1 -> {out_dir/'fig1_kg.pdf'}  ({FIG_W_IN} x {FIG_H_IN} in, node text {FS_NODE} pt)")


if __name__ == "__main__":
    make(Path(__file__).parent / "figures")
