#!/usr/bin/env python3
"""render_structural_summary.py — render the logical skeleton of the text as a clean diagram.

Usage:
    python3 render/render_structural_summary.py data/projections/essay/structural_summary.json
"""

import json
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_PNG = Path("data/videos/structural_summary.png")

SECTION_COLORS = {
    "Premises":         "#4A90D9",
    "Definitions":      "#7BC67E",
    "Contested":        "#E8A838",
    "Contradictions":   "#E05C5C",
    "Resolutions":      "#88FF88",
    "Open Variables":   "#FF9966",
}


def render_section(ax, y_start: float, title: str, items: list[str],
                   color: str, max_items: int = 5) -> float:
    ax.text(0.02, y_start, title, color=color, fontsize=9,
            transform=ax.transAxes, fontweight="bold")
    y = y_start - 0.04
    for item in items[:max_items]:
        wrapped = textwrap.wrap(str(item)[:80], 85)
        for line in wrapped[:2]:
            ax.text(0.04, y, f"• {line}", color="white", fontsize=7,
                    transform=ax.transAxes)
            y -= 0.035
    if len(items) > max_items:
        ax.text(0.04, y, f"  … {len(items) - max_items} more",
                color="#888888", fontsize=6, transform=ax.transAxes)
        y -= 0.03
    return y - 0.02


def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 14))
    fig.patch.set_facecolor("#0d0d1a")
    ax.set_facecolor("#0d0d1a")
    ax.axis("off")

    y = 0.97

    stats = (
        f"claims: {data.get('total_claims', 0)}  "
        f"entities: {data.get('total_entities', 0)}  "
        f"transformations: {data.get('transformation_count', 0)}"
    )
    ax.text(0.5, y, "Structural Summary", color="white",
            fontsize=13, ha="center", transform=ax.transAxes, fontweight="bold")
    y -= 0.04
    ax.text(0.5, y, stats, color="#888888", fontsize=8,
            ha="center", transform=ax.transAxes)
    y -= 0.05

    sections = [
        ("Premises",       data.get("premises", [])),
        ("Definitions",    data.get("definitions", [])),
        ("Contested",      data.get("contested_claims", [])),
        ("Resolutions",    [r["ambiguity"] for r in data.get("resolutions", [])]),
        ("Open Variables", data.get("open_variables", [])),
    ]

    for title, items in sections:
        if items:
            color = SECTION_COLORS.get(title, "#AAAAAA")
            y = render_section(ax, y, title, items, color)
            if y < 0.05:
                break

    # Contradictions
    contras = data.get("contradictions", [])
    if contras:
        color = SECTION_COLORS["Contradictions"]
        ax.text(0.02, max(y, 0.05), "Contradictions", color=color,
                fontsize=9, transform=ax.transAxes, fontweight="bold")
        y2 = max(y, 0.05) - 0.04
        for c in contras[:3]:
            ax.text(0.04, y2,
                    f"• {str(c.get('claim_a',''))[:40]} ↔ {str(c.get('claim_b',''))[:40]}",
                    color="white", fontsize=7, transform=ax.transAxes)
            y2 -= 0.035

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=130, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close()
    print(f"Saved: {OUT_PNG}")


if __name__ == "__main__":
    main()
