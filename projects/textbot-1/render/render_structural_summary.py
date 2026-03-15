#!/usr/bin/env python3
"""
Render structural summary projection as a logic diagram image.
Requires: matplotlib
"""

import json
import sys
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
except ImportError:
    print("Missing dependencies: pip install matplotlib")
    raise


def wrap(text, width=45):
    words = text.split()
    lines, line = [], []
    for w in words:
        if sum(len(x) + 1 for x in line) + len(w) > width:
            lines.append(" ".join(line))
            line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))
    return "\n".join(lines[:2])


def draw_section(ax, items, label, y_start, color, x=0.5):
    ax.text(x, y_start + 0.015, label, color=color, fontsize=9,
            ha="center", va="bottom", fontweight="bold")
    for i, item in enumerate(items[:6]):
        text = item.get("text") or item.get("label") or item.get("term") or ""
        y = y_start - 0.06 * (i + 1)
        rect = mpatches.FancyBboxPatch(
            (0.05, y - 0.022), 0.90, 0.04,
            boxstyle="round,pad=0.005",
            linewidth=1, edgecolor=color, facecolor="#060f06"
        )
        ax.add_patch(rect)
        ax.text(0.50, y, wrap(text), color="#aaffcc", fontsize=7,
                ha="center", va="center")
    return y_start - 0.06 * (min(len(items), 6) + 2)


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path("videos").mkdir(exist_ok=True)

    premises   = data.get("premises", [])
    defs       = data.get("definitions", [])
    contras    = data.get("contradictions", [])
    resols     = data.get("resolutions", [])
    open_vars  = data.get("open_variables", [])

    total = len(premises) + len(defs) + len(contras) + len(resols) + len(open_vars)
    fig_h = max(8, total * 0.5 + 4)

    fig, ax = plt.subplots(figsize=(12, fig_h))
    fig.patch.set_facecolor("#0a0a0f")
    ax.set_facecolor("#0a0a0f")
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    y = 0.96
    if premises:
        y = draw_section(ax, premises, "PREMISES", y, "#00ff88")
    if defs:
        y = draw_section(ax, defs, "DEFINITIONS", y, "#88ddff")
    if contras:
        y = draw_section(ax, contras, "CONTRADICTIONS", y, "#ff6666")
    if resols:
        y = draw_section(ax, resols, "RESOLUTIONS", y, "#ffdd88")
    if open_vars:
        y = draw_section(ax, open_vars, "OPEN VARIABLES", y, "#cc88ff")

    ax.set_title("Structural Summary", color="#88ffaa", fontsize=12, pad=10)
    plt.tight_layout()
    plt.savefig("videos/structural_summary.png", dpi=150, facecolor="#0a0a0f")
    plt.close()
    print("Rendered: videos/structural_summary.png")


if __name__ == "__main__":
    main()
