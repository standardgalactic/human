#!/usr/bin/env python3
"""
Render timeline causality projection as a horizontal timeline image.
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
    import numpy as np
except ImportError:
    print("Missing dependencies: pip install matplotlib numpy")
    raise


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path("videos").mkdir(exist_ok=True)

    timeline = data.get("timeline", [])
    if not timeline:
        print("No timeline to render.")
        return

    n = len(timeline)
    fig, ax = plt.subplots(figsize=(max(16, n * 2), 6))
    fig.patch.set_facecolor("#0a0a0f")
    ax.set_facecolor("#0a0a0f")

    xs = list(range(n))
    y = 0.5

    ax.plot(xs, [y] * n, color="#336633", linewidth=2, zorder=1)

    for i, event in enumerate(timeline):
        ax.scatter(i, y, s=200, color="#00ff88", zorder=3)
        label = event.get("label", event.get("event_id", ""))[:30]
        ax.text(i, y + 0.12, label, color="#aaffcc", fontsize=8,
                ha="center", va="bottom", rotation=30)
        cause = event.get("cause", "")
        if cause:
            ax.text(i, y - 0.12, f"← {cause[:20]}", color="#ff8844",
                    fontsize=7, ha="center", va="top")

    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Timeline & Causality", color="#88ffaa", fontsize=13, pad=20)

    plt.tight_layout()
    plt.savefig("videos/timeline_causality.png", dpi=150, facecolor="#0a0a0f")
    plt.close()
    print("Rendered: videos/timeline_causality.png")


if __name__ == "__main__":
    main()
