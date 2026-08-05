"""Generate Figure 1 (the dependency graph K_G).

Standalone: `python analysis/make_fig1_kg.py`
Companion to make_fig2_route.py, which draws Figure 2.

Until v40 no script drew Figure 1: the PDF and PNG under analysis/figures/ were
hand-managed, which is exactly the drift the Appendix A table avoids by being
generated. Everything here is READ FROM depgraph.edges and depgraph.nodes, so a
change to the graph cannot leave the figure quietly wrong.

Two conventions the caption depends on, enforced here rather than assumed:

  1. One arrow per DISTINCT source-target pair, drawn at the STRONGEST grade
     that asserts it (A > B > C > narrative). Five pairs are asserted twice, so
     the 26 edges of E become 21 arrows.
  2. The legend lists only the grades that actually survive rule 1. Every
     grade-B pair is also asserted at grade A, so no arrow is drawn dashed and
     no grade-B key is printed. If a future edition of the Standards adds a
     grade-B pair with no grade-A counterpart, the key reappears by itself.

Layout fixes over the hand-made figure: boxes are sized from the rendered text
extent, so long names (HvyAlcoholConsump, HeartDiseaseorAttack) no longer clip;
the canvas is saved with a tight bounding box, so the figure is not offset
inside its frame.
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
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from depgraph.edges import EDGES
from depgraph.nodes import TIER

OUT = Path(__file__).parent / "figures"
OUT.mkdir(exist_ok=True)

# --------------------------------------------------------------- graph facts
# Strongest first; the last entry is the module's marker for an ungraded edge.
UNGRADED = "-"          # depgraph.edges marks a narrative edge with "-"
GRADE_ORDER = ["A", "B", "C", UNGRADED]

GRADE_STYLE = {
    "A": dict(ls="solid", color="#1F3A4D", lw=1.15, label="ADA grade A"),
    "B": dict(ls=(0, (4.5, 2.0)), color="#3E6480", lw=1.05, label="ADA grade B"),
    "C": dict(ls=(0, (1.2, 1.7)), color="#6E93A8", lw=1.05, label="ADA grade C"),
    UNGRADED: dict(ls="solid", color="#D3A24C", lw=0.95,
                   label="section narrative"),
}


def strongest_per_pair():
    """One (src, dst) -> grade mapping, at the strongest grade asserting it."""
    best: dict[tuple[str, str], str] = {}
    for e in EDGES:
        key = (e.src, e.dst)
        if key not in best or GRADE_ORDER.index(e.grade) < GRADE_ORDER.index(best[key]):
            best[key] = e.grade
    return best


ARROWS = strongest_per_pair()

assert len(EDGES) == 26, f"expected 26 edges, got {len(EDGES)}"
assert len(ARROWS) == 21, f"expected 21 distinct pairs, got {len(ARROWS)}"
assert not any(TIER[s] == "indicator" for s, _ in ARROWS), \
    "the caption claims indicators are sinks: no edge may originate there"
assert all(g == UNGRADED for (_, d), g in ARROWS.items()
           if TIER[d] == "indicator"), \
    "the caption claims every edge into the indicator tier is ungraded"

DRAWN_GRADES = [g for g in GRADE_ORDER if g in set(ARROWS.values())]

# ------------------------------------------------------------------- layout
BANDS = [
    ("LEVER", "lever", "#1F7A32", "#EDF6EE",
     ["Fruits", "Veggies", "PhysActivity", "BMI", "Smoker",
      "HvyAlcoholConsump", "NoDocbcCost"]),
    ("TREATABLE", "treatable", "#1565C0", "#EDF3FB",
     ["HighBP", "HighChol"]),
    ("INDICATOR", "indicator", "#C62828", "#FBEDED",
     ["GenHlth", "PhysHlth", "MentHlth", "DiffWalk"]),
    ("IMMUTABLE / proxy", "immutable", "#8A8A8A", "#F4F4F4",
     ["Age", "Sex", "Stroke", "HeartDiseaseorAttack", "Income", "Education",
      "AnyHealthcare", "CholCheck"]),
]

for _, tier, _, _, members in BANDS:
    assert {f for f, t in TIER.items() if t == tier} == set(members), \
        f"band {tier!r} is out of step with depgraph.nodes.TIER"

# Names too long to sit on one line at 7 pt inside a 21-node row.
WRAP = {
    "HvyAlcoholConsump": "HvyAlcohol\nConsump",
    "HeartDiseaseorAttack": "HeartDisease\norAttack",
    "NoDocbcCost": "NoDocbc\nCost",
    "AnyHealthcare": "Any\nHealthcare",
}

BAND_Y = {"lever": 3.00, "treatable": 2.10, "indicator": 1.20, "immutable": 0.18}
BAND_H = 0.42
X0, X1 = 0.90, 9.85          # inner span available to the node rows
FS_NODE = 7.0

plt.rcParams.update({"font.family": "sans-serif", "font.size": 7.5})


def text_width(fig, s, fontsize):
    """Width of `s` in axes-data units, measured, not guessed."""
    t = fig.text(0, 0, s, fontsize=fontsize)
    fig.canvas.draw()
    bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
    t.remove()
    return bb.width


fig, ax = plt.subplots(figsize=(6.9, 3.45))
ax.set_xlim(0, 10.4)
ax.set_ylim(-0.30, 4.32)
ax.axis("off")
fig.canvas.draw()
px_per_unit = ax.transData.transform((1, 0))[0] - ax.transData.transform((0, 0))[0]

POS: dict[str, tuple[float, float, float]] = {}   # name -> (cx, cy, half-width)

for label, tier, ink, fill, members in BANDS:
    y = BAND_Y[tier]
    ax.add_patch(FancyBboxPatch((0.62, y - 0.09), 9.66, BAND_H + 0.18,
                                boxstyle="round,pad=0.005", lw=0, fc=fill,
                                zorder=0))
    ax.text(0.52, y + BAND_H / 2, label, ha="right", va="center",
            fontsize=8.2, fontweight="bold", color=ink, zorder=1)

    widths = []
    for m in members:
        lines = WRAP.get(m, m).split("\n")
        w = max(text_width(fig, ln, FS_NODE) for ln in lines) / px_per_unit
        widths.append(w + 0.30)                     # padding inside the box
    gap = (X1 - X0 - sum(widths)) / (len(members) - 1)
    x = X0
    for m, w in zip(members, widths):
        ax.add_patch(FancyBboxPatch((x, y), w, BAND_H,
                                    boxstyle="round,pad=0.018",
                                    lw=0.85, ec=ink, fc="white", zorder=3))
        ax.text(x + w / 2, y + BAND_H / 2, WRAP.get(m, m), ha="center",
                va="center", fontsize=FS_NODE, zorder=4,
                fontweight="bold" if m == "BMI" else "normal",
                linespacing=0.95, color="#111111")
        POS[m] = (x + w / 2, y, w / 2)
        x += w + gap

# ------------------------------------------------------------------- arrows
def anchor(name, other_x, top: bool):
    """Leave from the side the target lies on, so labels stay readable."""
    cx, y, hw = POS[name]
    yy = y + BAND_H if top else y
    dx = max(-hw * 0.78, min(hw * 0.78, (other_x - cx) * 0.16))
    return cx + dx, yy


for (src, dst), grade in sorted(ARROWS.items(),
                                key=lambda kv: GRADE_ORDER.index(kv[1]),
                                reverse=True):
    st = GRADE_STYLE[grade]
    same_band = TIER[src] == TIER[dst]
    if same_band:
        # Fruits/Veggies/PhysActivity -> BMI all live in the lever band. Arc
        # them over the top of the row so they do not vanish behind the boxes.
        a = (POS[src][0], BAND_Y[TIER[src]] + BAND_H)
        b = (POS[dst][0], BAND_Y[TIER[dst]] + BAND_H)
        rad = -0.34
    else:
        a = anchor(src, POS[dst][0], top=False)
        b = anchor(dst, POS[src][0], top=True)
        rad = 0.13 if POS[dst][0] >= POS[src][0] else -0.13
    ax.add_patch(FancyArrowPatch(
        a, b, arrowstyle="-|>", mutation_scale=7.5,
        connectionstyle=f"arc3,rad={rad}", lw=st["lw"], color=st["color"],
        linestyle=st["ls"], shrinkA=1.0, shrinkB=1.0, zorder=2,
        clip_on=False))

# The gap the immutable band sits below: no intervention route crosses it.
sep = (BAND_Y["indicator"] - 0.09 + BAND_Y["immutable"] + BAND_H + 0.09) / 2
ax.plot([0.62, 10.28], [sep, sep], lw=0.7, ls=(0, (1.4, 2.4)), color="#BBBBBB",
        zorder=1)
ax.text(10.28, sep + 0.05, "no edges cross", ha="right", va="bottom",
        fontsize=6.6, style="italic", color="#999999")

handles = [Line2D([0], [0], color=GRADE_STYLE[g]["color"],
                  lw=GRADE_STYLE[g]["lw"] + 0.25, linestyle=GRADE_STYLE[g]["ls"],
                  label=GRADE_STYLE[g]["label"]) for g in DRAWN_GRADES]
ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.055),
          ncol=len(handles), frameon=False, fontsize=7.4, handlelength=2.6,
          columnspacing=2.2)

fig.savefig(OUT / "fig1_kg.pdf", bbox_inches="tight", pad_inches=0.02)
fig.savefig(OUT / "fig1_kg.png", bbox_inches="tight", pad_inches=0.02, dpi=600)
print(f"wrote {OUT / 'fig1_kg.pdf'} and .png")
print(f"  {len(EDGES)} edges -> {len(ARROWS)} arrows; "
      f"grades drawn: {', '.join(DRAWN_GRADES)}")
