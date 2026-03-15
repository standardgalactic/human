#!/usr/bin/env python3
"""
Render character state projection as radar/bar charts per character.
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

    characters = data.get("characters", [])
    if not characters:
        print("No characters to render.")
        return

    n_chars = len(characters)
    fig, axes = plt.subplots(1, n_chars, figsize=(max(8, n_chars * 4), 5))
    fig.patch.set_facecolor("#0a0a0f")

    if n_chars == 1:
        axes = [axes]

    for ax, char in zip(axes, characters):
        ax.set_facecolor("#060f06")
        name = char.get("name", "unknown")
        explicit = char.get("initial_state", {}).get("explicit_attributes", [])
        uncertain = char.get("initial_state", {}).get("uncertain_attributes", [])
        changes = char.get("state_changes", [])

        categories = ["explicit attrs", "uncertain attrs", "state changes"]
        values = [len(explicit), len(uncertain), len(changes)]

        bars = ax.barh(categories, values, color=["#00ff88", "#ff8844", "#88ddff"])
        ax.set_facecolor("#060f06")
        ax.tick_params(colors="white", labelsize=8)
        ax.set_title(name[:20], color="#88ffaa", fontsize=10)
        for spine in ax.spines.values():
            spine.set_edgecolor("#336633")

    plt.suptitle("Character State Vectors", color="#88ffaa", fontsize=13)
    plt.tight_layout()
    plt.savefig("videos/character_state.png", dpi=150, facecolor="#0a0a0f")
    plt.close()
    print("Rendered: videos/character_state.png")


if __name__ == "__main__":
    main()
