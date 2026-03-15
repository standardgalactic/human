#!/usr/bin/env python3
"""
Render procedural transform projection as a flowchart image.
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


def wrap(text, width=22):
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
    return "\n".join(lines[:3])


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path("videos").mkdir(exist_ok=True)

    steps = data.get("steps", [])
    if not steps:
        print("No steps to render.")
        return

    n = len(steps)
    fig_h = max(6, n * 1.4)
    fig, ax = plt.subplots(figsize=(10, fig_h))
    fig.patch.set_facecolor("#0a0a0f")
    ax.set_facecolor("#0a0a0f")
    ax.axis("off")

    box_w, box_h = 0.6, 0.06
    x_center = 0.5
    y_start = 0.96
    y_step = 1.0 / (n + 1)

    for i, step in enumerate(steps):
        y = y_start - i * y_step
        label = wrap(step.get("operation", step.get("step_id", "")))

        rect = mpatches.FancyBboxPatch(
            (x_center - box_w / 2, y - box_h / 2),
            box_w, box_h,
            boxstyle="round,pad=0.01",
            linewidth=1,
            edgecolor="#00ff88",
            facecolor="#060f06"
        )
        ax.add_patch(rect)
        ax.text(x_center, y, label, color="#aaffcc", fontsize=8,
                ha="center", va="center")

        if i < n - 1:
            y_arrow_start = y - box_h / 2
            y_arrow_end = y - y_step + box_h / 2
            ax.annotate("", xy=(x_center, y_arrow_end),
                        xytext=(x_center, y_arrow_start),
                        arrowprops=dict(arrowstyle="->", color="#336633"))

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title("Procedural Transformations", color="#88ffaa", fontsize=12, pad=10)

    plt.tight_layout()
    plt.savefig("videos/procedural_transform.png", dpi=150, facecolor="#0a0a0f")
    plt.close()
    print("Rendered: videos/procedural_transform.png")


if __name__ == "__main__":
    main()
