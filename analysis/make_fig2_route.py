"""Generate Figure 2 (route support is a property of the pair).

Standalone: `python analysis/make_fig2_route.py`
Companion to make_figures.py, which draws Figure 1.

Two counterfactuals from the reference run, both moving BMI, both moving a
self-reported indicator, one admissible and one not. Drawn from
outputs/raw_cf_changes.csv:

    patient 8, cf 0    BMI 44 -> 26.9   PhysHlth 30 -> 25    admitted
    patient 3, cf 4    BMI 48 -> 30.6   MentHlth 20 -> 12    blocked

The edge facts are READ FROM depgraph.edges rather than written into this file,
so that a change to the edge set cannot leave the figure quietly wrong. If the
pairs below stop matching the graph, the script fails loudly instead of drawing
a false picture.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import matplotlib
matplotlib.use("Agg")
# TrueType, not Type 3: IEEE PDF eXpress rejects Type 3 fonts, and Elsevier
# production prefers embedded TrueType as well.
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from depgraph.edges import EDGES
from depgraph.nodes import TIER

OUT = Path(__file__).parent / "figures"
OUT.mkdir(exist_ok=True)

# ------------------------------------------------------------------ graph facts
def edge_between(src: str, dst: str):
    hits = [e for e in EDGES if e.src == src and e.dst == dst]
    return hits[0] if hits else None


def lever_routes_into(dst: str):
    return sorted({e.src for e in EDGES
                   if e.dst == dst and TIER.get(e.src) == "lever"})


SUPPORTED = edge_between("BMI", "PhysHlth")
assert SUPPORTED is not None, "panel (a) assumes BMI -> PhysHlth is in K_G"
assert edge_between("BMI", "MentHlth") is None, \
    "panel (b) assumes BMI -> MentHlth is NOT in K_G"
ALT = lever_routes_into("MentHlth")
assert ALT == ["PhysActivity"], f"panel (b) assumes one alternative route, got {ALT}"

SRC_A = SUPPORTED.source          # e.g. "SoC 2026, S8, obesity narrative"
SRC_B = edge_between(ALT[0], "MentHlth").source

plt.rcParams.update({
    "font.family": "serif", "font.size": 9, "axes.linewidth": 0.6,
})

INK, MUTE, GHOST = "#111111", "#666666", "#AAAAAA"


def box(ax, xy, w, h, label, sub, tier, ghost=False):
    ec = GHOST if ghost else INK
    fc = "#FFFFFF" if not ghost else "#FAFAFA"
    ls = (0, (2, 2)) if ghost else "solid"
    ax.add_patch(FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.012",
                                lw=0.9, ec=ec, fc=fc, linestyle=ls, zorder=3))
    cx, cy = xy[0] + w / 2, xy[1] + h / 2
    ax.text(cx, cy + 0.055, label, ha="center", va="center", zorder=4,
            fontsize=9.5, color=ec, fontweight="bold" if not ghost else "normal")
    ax.text(cx, cy - 0.052, sub, ha="center", va="center", zorder=4,
            fontsize=8, color=GHOST if ghost else MUTE)
    ax.text(cx, xy[1] - 0.045, tier, ha="center", va="top", fontsize=7.2,
            color=GHOST if ghost else MUTE, style="italic")


def arrow(ax, a, b, text, ok=True, ghost=False):
    col = GHOST if ghost else INK
    st = "solid" if ok and not ghost else (0, (2.5, 2.5))
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11,
                                 lw=1.0, color=col, linestyle=st, zorder=2,
                                 shrinkA=2, shrinkB=2))
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    ax.text(mx, my + 0.035, text, ha="center", va="bottom", fontsize=7.4,
            color=col, zorder=5,
            bbox=dict(fc="white", ec="none", pad=1.0))


fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.05))
W, H = 0.30, 0.19
YTOP, YBOT = 0.66, 0.30          # rows: main pair, ghost route
YV = 0.10                        # verdict, identical in both panels

# ---------------------------------------------------------------- admitted
ax = axes[0]
box(ax, (0.06, YTOP), W, H, "BMI", "44.0 $\\rightarrow$ 26.9", "lever")
box(ax, (0.62, YTOP), W, H, "PhysHlth", "30 $\\rightarrow$ 25", "indicator")
arrow(ax, (0.36, YTOP + H / 2), (0.62, YTOP + H / 2),
      f"{SRC_A}")
ax.text(0.5, YV, "ADMITTED", ha="center", fontsize=10, fontweight="bold")
ax.text(0.5, YV - 0.09,
        "the indicator moves, and the same counterfactual\n"
        "moves a lever that has an edge into it",
        ha="center", va="top", fontsize=7.6, color=MUTE)
ax.set_title("(a) route support present", fontsize=9, pad=4)

# ----------------------------------------------------------------- blocked
ax = axes[1]
box(ax, (0.06, YTOP), W, H, "BMI", "48.0 $\\rightarrow$ 30.6", "lever")
box(ax, (0.62, YTOP), W, H, "MentHlth", "20 $\\rightarrow$ 12", "indicator")
ym = YTOP + H / 2
ax.plot([0.36, 0.62], [ym, ym], lw=0.9, ls=(0, (2, 2)), color=GHOST, zorder=2)
ax.text(0.49, ym + 0.035, "no edge", ha="center", va="bottom", fontsize=7.4,
        color=GHOST, bbox=dict(fc="white", ec="none", pad=1.0))
ax.plot(0.49, ym, marker="x", ms=6.5, mew=1.4, color=INK, zorder=6)
box(ax, (0.06, YBOT), W, H, "PhysActivity", "unchanged", "lever", ghost=True)
arrow(ax, (0.36, YBOT + H / 2), (0.66, YTOP - 0.005),
      f"the only route: {SRC_B}", ghost=True)
ax.text(0.5, YV, "BLOCKED", ha="center", fontsize=10, fontweight="bold")
ax.text(0.5, YV - 0.09,
        "the only lever the guideline recognises as a route\n"
        "into this indicator is not the one that moved",
        ha="center", va="top", fontsize=7.6, color=MUTE)
ax.set_title("(b) route support absent", fontsize=9, pad=4)

for ax in axes:
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.12, 0.94)
    ax.axis("off")

fig.subplots_adjust(bottom=0.16, wspace=0.06)
fig.text(0.5, 0.015,
         "The same lever moves in both. Admissibility depends on which indicator "
         "it is paired with, which is why a\nconstraint table indexed by feature "
         "cannot express the condition.",
         ha="center", fontsize=7.8, color=MUTE)

fig.savefig(OUT / "fig2_route.pdf")
fig.savefig(OUT / "fig2_route.png", dpi=220)
print(f"wrote {OUT / 'fig2_route.pdf'} and .png")
