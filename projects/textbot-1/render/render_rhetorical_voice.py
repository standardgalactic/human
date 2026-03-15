#!/usr/bin/env python3
"""
Render rhetorical voice projection as an argument structure diagram.
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


STANCE_COLORS = {
    "assertion":   "#00ff88",
    "definition":  "#88ddff",
    "analogy":     "#ffdd88",
    "objection":   "#ff6666",
    "concession":  "#ff8844",
    "speculation": "#cc88ff",
}


def wrap(text, width=40):
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


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path("videos").mkdir(exist_ok=True)

    claims = data.get("claims", [])
    if not claims:
        print("No claims to render.")
        return

    n = len(claims)
    fig, ax = plt.subplots(figsize=(14, max(6, n * 0.8)))
    fig.patch.set_facecolor("#0a0a0f")
    ax.set_facecolor("#0a0a0f")
    ax.axis("off")

    for i, claim in enumerate(claims):
        y = 1.0 - (i + 1) / (n + 1)
        ctype = claim.get("type", "assertion")
        color = STANCE_COLORS.get(ctype, "#aaaaaa")
        label = wrap(claim.get("text", ""))

        rect = mpatches.FancyBboxPatch(
            (0.12, y - 0.03), 0.75, 0.06,
            boxstyle="round,pad=0.01",
            linewidth=1,
            edgecolor=color,
            facecolor="#060f06"
        )
        ax.add_patch(rect)
        ax.text(0.50, y, label, color="#aaffcc", fontsize=8, ha="center", va="center")
        ax.text(0.08, y, ctype, color=color, fontsize=7, ha="right", va="center")

    legend_handles = [
        mpatches.Patch(color=v, label=k) for k, v in STANCE_COLORS.items()
    ]
    ax.legend(handles=legend_handles, loc="lower right", facecolor="#0a0a0f",
              labelcolor="white", fontsize=7)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title("Rhetorical Structure", color="#88ffaa", fontsize=12, pad=10)

    plt.tight_layout()
    plt.savefig("videos/rhetorical_voice.png", dpi=150, facecolor="#0a0a0f")
    plt.close()
    print("Rendered: videos/rhetorical_voice.png")


if __name__ == "__main__":
    main()
