#!/usr/bin/env python3
"""render_character_state.py — render entity state evolution as small multiples.

Each character gets a panel showing how many state-change events affected it
and which attributes were constrained at each step.

Usage:
    python3 render/render_character_state.py data/projections/essay/character_state.json
"""

import json
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_PNG = Path("data/videos/character_state.png")


def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)

    characters = data.get("characters", [])
    if not characters:
        print("WARNING: no characters to render")
        return

    n = len(characters)
    cols = min(3, n)
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 4 * rows))
    fig.patch.set_facecolor("#0d0d1a")

    # Flatten axes for uniform iteration
    if n == 1:
        axes_flat = [axes]
    else:
        axes_flat = [ax for row in (axes if rows > 1 else [axes]) for ax in (row if cols > 1 else [row])]

    for idx, char in enumerate(characters):
        ax = axes_flat[idx]
        ax.set_facecolor("#12122a")
        ax.axis("off")

        name = char["name"]
        changes = char.get("state_changes", [])
        certainty = char.get("final_certainty", 0.2)
        uncertain = char.get("initial_state", {}).get("uncertain_attributes", [])

        ax.text(0.5, 0.92, name, color="#FFDD44", fontsize=11,
                ha="center", transform=ax.transAxes, fontweight="bold")

        ax.text(0.5, 0.80, f"Final certainty: {certainty:.2f}",
                color="#88FF88", fontsize=8, ha="center", transform=ax.transAxes)

        if uncertain:
            utext = "Initially uncertain: " + ", ".join(uncertain[:4])
            ax.text(0.5, 0.70, "\n".join(textwrap.wrap(utext, 38)),
                    color="#FF9966", fontsize=7, ha="center",
                    transform=ax.transAxes, style="italic")

        for j, sc in enumerate(changes[:6]):
            y = 0.58 - j * 0.10
            label = f"• {sc['event_label'][:40]}"
            constrained = sc.get("attributes_constrained", [])
            color = "#AADDFF" if not constrained else "#AAFFAA"
            ax.text(0.05, y, label, color=color, fontsize=7,
                    transform=ax.transAxes, va="top")
            if constrained:
                ax.text(0.08, y - 0.06,
                        "  ↳ resolved: " + ", ".join(constrained[:2]),
                        color="#88FF88", fontsize=6,
                        transform=ax.transAxes, va="top", style="italic")

        if len(changes) > 6:
            ax.text(0.05, 0.58 - 6 * 0.10,
                    f"  … {len(changes) - 6} more events",
                    color="#888888", fontsize=6, transform=ax.transAxes)

    # Hide unused panels
    for idx in range(n, len(axes_flat)):
        axes_flat[idx].axis("off")
        axes_flat[idx].set_facecolor("#0d0d1a")

    fig.suptitle("Character State Evolution", color="white", fontsize=13, y=1.01)
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=130, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close()
    print(f"Saved: {OUT_PNG}")


if __name__ == "__main__":
    main()
