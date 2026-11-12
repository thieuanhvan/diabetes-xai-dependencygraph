"""Architecture figure for the ESWA v3 manuscript: guideline text to graph, derived constraints, generators, audit.
Writes vector PDF, EPS and SVG and a 1000 dpi PNG to outputs/journal_main/figures_v3/.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
                            "font.family": "DejaVu Sans", "font.size": 8})
OUT = Path(r"D:\20-study\uit\research\diabetesxai\paper7\outputs\journal_main\figures_v3")
OUT.mkdir(parents=True, exist_ok=True)

INK, KB, ENG, DATA = "#222222", "#dbe8f5", "#fbe5c8", "#e4e4e4"
fig, ax = plt.subplots(figsize=(7.2, 4.3))
ax.set_xlim(0, 100)
ax.set_ylim(-4, 58)
ax.axis("off")


def box(x, y, w, h, title, lines, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec=INK, lw=0.8))
    ax.text(x + w / 2, y + h - 2.3, title, ha="center", va="top", fontsize=7.8, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + h - 6.2, "\n".join(lines), ha="center", va="top", fontsize=6.7, color=INK,
            linespacing=1.25)


def arrow(p, q, label=None, off=(0, 1.6)):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=10, lw=0.9, color=INK))
    if label:
        ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], label, ha="center", va="bottom",
                fontsize=6.9, style="italic", color="#444444")


# top row: knowledge acquisition, knowledge base, audit
box(1, 38, 21.5, 18, "Guideline text", ["ADA 2026, MoH Vietnam,", "NICE NG28,", "WHO HEARTS-D,", "KDIGO 2024"], DATA)
box(26.5, 38, 21.5, 18, "Extraction", ["two sessions with", "separate prompts;", "quotation check;",
                                       "agreed edges kept"], ENG)
box(52, 38, 21.5, 18, "Dependency graph", ["RDF/Turtle: roles,", "reified routes with", "authority, page and",
                                           "strength; codes"], KB)
box(77.5, 38, 21.5, 18, "SPARQL audit", ["touches indicator,", "unsupported, fully", "unactionable; Python",
                                         "cross-check"], ENG)
arrow((23, 47), (26, 47))
arrow((48.5, 47), (51.5, 47))
arrow((74, 47), (77, 47))

# bottom row: derivation and generation
box(1, 4, 21.5, 20, "Survey data, model", ["BRFSS, NHIS, NHANES;", "XGBoost, logistic", "regression, random",
                                           "forest, neural network"], DATA)
box(26.5, 4, 21.5, 20, "Derived constraints", ["role table, lock set", "(indicators fixed);", "route rule: an indicator",
                                               "moves only with a lever", "that has a route into it"], KB)
box(52, 4, 21.5, 20, "Generators", ["DiCE, exhaustive search,", "Wachter, Growing", "Spheres, Actionable",
                                    "Recourse; published,", "lock, route-aware"], ENG)
box(77.5, 4, 21.5, 20, "Counterfactuals", ["change sets and", "values per patient", "and mode"], DATA)
arrow((62.7, 37.6), (37.3, 24.6), "derive by script", off=(-4, 1.0))
arrow((48.5, 14), (51.5, 14))
ax.plot([11.7, 11.7, 62.7], [3.4, -1.8, -1.8], color=INK, lw=0.9)
arrow((62.7, -1.8), (62.7, 3.4))
ax.text(37, -1.4, "model to explain", ha="center", va="bottom", fontsize=6.6, style="italic", color="#444444")
arrow((74, 14), (77, 14))
arrow((88.2, 24.6), (88.2, 37.4), "audit", off=(3.2, -1))

for ext in ("pdf", "eps", "svg"):
    fig.savefig(OUT / f"fig1_architecture.{ext}", bbox_inches="tight", pad_inches=0.03)
fig.savefig(OUT / "fig1_architecture.png", bbox_inches="tight", pad_inches=0.03, dpi=1000)
print("written", sorted(p.name for p in OUT.glob("fig1_architecture.*")))
