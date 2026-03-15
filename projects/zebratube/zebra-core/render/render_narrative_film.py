#!/usr/bin/env python3
"""render_narrative_film.py — render scenes as storyboard slides (PNG strip + optional MP4).

Usage:
    python3 render/render_narrative_film.py data/projections/essay/narrative_film.json
"""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FRAMES_DIR = Path("data/frames/narrative_film")
OUT_VIDEO   = Path("data/videos/narrative_film.mp4")
FPS = 1


def wrap(text: str, width: int = 40) -> str:
    return "\n".join(textwrap.wrap(text, width))


def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    OUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)

    scenes = data.get("scenes", [])
    if not scenes:
        print("WARNING: no scenes to render")
        return

    for i, scene in enumerate(scenes):
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#1a1a2e")
        ax.axis("off")

        # Scene number badge
        ax.text(0.03, 0.93, f"SCENE {i+1}/{len(scenes)}",
                color="#FFDD44", fontsize=9, transform=ax.transAxes,
                fontfamily="monospace")

        # Summary (headline)
        ax.text(0.5, 0.75, wrap(scene["summary"], 50),
                color="white", fontsize=12, transform=ax.transAxes,
                ha="center", va="top", fontweight="bold")

        # Characters
        chars = ", ".join(scene["characters"]) if scene["characters"] else "—"
        ax.text(0.5, 0.48, f"Characters: {wrap(chars, 60)}",
                color="#88BBFF", fontsize=9, transform=ax.transAxes, ha="center")

        # Location
        loc = scene.get("location") or "unspecified"
        ax.text(0.5, 0.38, f"Location: {loc}",
                color="#AAAAAA", fontsize=9, transform=ax.transAxes, ha="center")

        # Uncertain details
        uncertain = scene.get("uncertain_details", [])
        if uncertain:
            utext = "Underdetermined: " + "; ".join(uncertain[:3])
            ax.text(0.5, 0.22, wrap(utext, 70),
                    color="#FF9966", fontsize=8, transform=ax.transAxes,
                    ha="center", style="italic")

        # Textual basis
        basis = scene.get("textual_basis", [])
        if basis:
            btext = f'"{basis[0][:60]}"'
            ax.text(0.5, 0.10, btext, color="#666688", fontsize=7,
                    transform=ax.transAxes, ha="center", style="italic")

        frame_path = FRAMES_DIR / f"frame_{i:03d}.png"
        plt.savefig(frame_path, dpi=120, facecolor=fig.get_facecolor())
        plt.close()

    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", str(FRAMES_DIR / "frame_%03d.png"),
            "-vf", "scale=1200:720",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(OUT_VIDEO),
        ], check=True, capture_output=True)
        print(f"Saved: {OUT_VIDEO}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"ffmpeg unavailable — frames saved to {FRAMES_DIR}/")


if __name__ == "__main__":
    main()
