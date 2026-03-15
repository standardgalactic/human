#!/usr/bin/env python3
"""
Render sonic mapping projection as a tension/tempo waveform image.
Requires: matplotlib
"""

import json
import sys
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Missing dependencies: pip install matplotlib numpy")
    raise


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path("videos").mkdir(exist_ok=True)

    segments = data.get("segments", [])
    if not segments:
        print("No segments to render.")
        return

    labels = [s.get("span_summary", "")[:20] for s in segments]
    tensions = [s.get("tension", 0.5) for s in segments]
    tempos = {"slow": 0.2, "moderate": 0.5, "fast": 0.8,
              "accelerating": 0.7, "decelerating": 0.3}
    tempo_vals = [tempos.get(s.get("tempo", "moderate"), 0.5) for s in segments]

    xs = list(range(len(segments)))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(max(14, len(segments) * 1.5), 8),
                                    sharex=True)
    fig.patch.set_facecolor("#0a0a0f")

    for ax in (ax1, ax2):
        ax.set_facecolor("#060f06")
        for spine in ax.spines.values():
            spine.set_edgecolor("#336633")
        ax.tick_params(colors="#88ffaa")

    ax1.plot(xs, tensions, color="#ff8844", linewidth=2, marker="o", markersize=5)
    ax1.fill_between(xs, tensions, alpha=0.2, color="#ff8844")
    ax1.set_ylabel("Tension", color="#88ffaa", fontsize=10)
    ax1.set_ylim(0, 1)
    ax1.set_title("Sonic Mapping — Tension & Tempo Arc", color="#88ffaa", fontsize=12)

    ax2.plot(xs, tempo_vals, color="#88ddff", linewidth=2, marker="s", markersize=5)
    ax2.fill_between(xs, tempo_vals, alpha=0.2, color="#88ddff")
    ax2.set_ylabel("Tempo", color="#88ffaa", fontsize=10)
    ax2.set_ylim(0, 1)
    ax2.set_xticks(xs)
    ax2.set_xticklabels(labels, rotation=35, ha="right", fontsize=7, color="#aaffcc")

    plt.tight_layout()
    plt.savefig("videos/sonic_mapping.png", dpi=150, facecolor="#0a0a0f")
    plt.close()
    print("Rendered: videos/sonic_mapping.png")


if __name__ == "__main__":
    main()
