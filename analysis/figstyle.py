"""Shared figure styling.

Colours come from the validated categorical palette; strategies are
assigned to slots in fixed order and never cycled, so a strategy keeps
its colour in every figure regardless of how many series are drawn.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SOFT = "#52514e"
INK_MUTED = "#8a8985"
GRID = "#e6e5e1"

# Categorical slots 1-4, fixed order.
SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]

STRATEGY_COLOR = {
    "still":         SLOT[3],
    "hide":          SLOT[2],
    "flee":          SLOT[1],
    "adaptive-dmas": SLOT[0],
}
STRATEGY_LABEL = {
    "still": "Still", "hide": "Hide", "flee": "Flee",
    "adaptive-dmas": "Adaptive",
}

# Diverging pair for signed advantage: blue <-> red, neutral gray middle.
DIVERGING = ["#0d366b", "#256abf", "#86b6ef", "#f0efec",
             "#f0a0a0", "#d03b3b", "#8b1a1a"]
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5",
              "#256abf", "#184f95", "#0d366b"]


def apply_base_style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK_SOFT,
        "axes.titlecolor": INK,
        "axes.titlesize": 11,
        "axes.titleweight": "semibold",
        "axes.labelsize": 9,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.frameon": False,
        "legend.fontsize": 8.5,
        "lines.linewidth": 2.0,
        "figure.dpi": 140,
    })


def strip_spines(ax, keep=("left", "bottom")):
    for side, spine in ax.spines.items():
        spine.set_visible(side in keep)


def title_block(fig, title, subtitle=None, y=0.975):
    fig.text(0.012, y, title, ha="left", va="top",
             fontsize=13, fontweight="semibold", color=INK)
    if subtitle:
        fig.text(0.012, y - 0.042, subtitle, ha="left", va="top",
                 fontsize=9, color=INK_SOFT)


def source_note(fig, text, y=0.012):
    fig.text(0.012, y, text, ha="left", va="bottom",
             fontsize=7.5, color=INK_MUTED)
