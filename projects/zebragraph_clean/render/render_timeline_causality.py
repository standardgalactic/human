#!/usr/bin/env python3
"""render_timeline_causality.py — draw causal event timeline as a static PNG.

Usage:
    python3 render/render_timeline_causality.py data/projections/essay/timeline_causality.json
"""

import json
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

OUT_PNG = Path("data/videos/timeline_causality.png")


def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)

    timeline = data.get("timeline", [])
    if not timeline:
        print("WARNING: empty timeline")
        return

    n = len(timeline)
    fig_height = max(6, n * 0.7)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    fig.patch.set_facecolor("#0d0d1a")
    ax.set_facecolor("#0d0d1a")
    ax.axis("off")

    # Vertical spine
    ax.axvline(x=0.35, ymin=0, ymax=1, color="#444466", linewidth=1.5)

    for i, entry in enumerate(timeline):
        y = 1.0 - (i + 0.5) / n

        # Node
        ax.scatter(0.35, y, s=120, color="#4A90D9", zorder=5)

        # Index badge
        ax.text(0.30, y, str(entry["index"]),
                color="#FFDD44", fontsize=8, ha="right", va="center",
                fontfamily="monospace")

        # Event label
        label = "\n".join(textwrap.wrap(entry["event"], 45))
        ax.text(0.38, y, label,
                color="white", fontsize=8, va="center")

        # Causes / effects annotations
        causes = entry.get("causes", [])
        effects = entry.get("effects", [])
        annotations = []
        if causes:
            annotations.append("← " + "; ".join(causes[:2])[:50])
        if effects:
            annotations.append("→ " + "; ".join(effects[:2])[:50])
        if annotations:
            ax.text(0.38, y - 0.5 / n,
                    "\n".join(annotations),
                    color="#AADDFF", fontsize=6, va="top", style="italic")

    ax.set_title("Timeline & Causality", color="white", fontsize=13, pad=12)
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=130, facecolor=fig.get_facecolor())
    plt.close()
    print(f"Saved: {OUT_PNG}")


if __name__ == "__main__":
    main()
