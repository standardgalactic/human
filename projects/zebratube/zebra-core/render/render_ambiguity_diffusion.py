#!/usr/bin/env python3
"""render_ambiguity_diffusion.py — animate the collapse of interpretation space.

Each frame shows open ambiguities as scattered points; resolved ones collapse
to the origin. The final frames show a tight cluster — the denouement.

Requires: matplotlib (ffmpeg must be on PATH for MP4 output)

Usage:
    python3 render/render_ambiguity_diffusion.py data/projections/essay/ambiguity_diffusion.json
"""

import json
import math
import random
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

FRAMES_DIR = Path("data/frames/ambiguity_diffusion")
OUT_VIDEO   = Path("data/videos/ambiguity_diffusion.mp4")
FPS = 2
SEED = 42


def spread_positions(n: int, radius: float, rng: random.Random) -> list[tuple[float, float]]:
    """Random positions inside a circle of given radius."""
    positions = []
    for _ in range(n):
        angle = rng.uniform(0, 2 * math.pi)
        r = radius * math.sqrt(rng.random())
        positions.append((r * math.cos(angle), r * math.sin(angle)))
    return positions


def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    OUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)

    units = data.get("units", [])
    if not units:
        print("WARNING: no ambiguity units to render")
        return

    rng = random.Random(SEED)

    # Assign stable positions for each ambiguity
    positions = {u["id"]: spread_positions(max(1, u["n_possibilities"]), 3.0, rng)
                 for u in units}

    # Build frames: each frame reveals one more collapsed ambiguity
    total_frames = len(units) + 2  # +2 for intro and final hold

    for frame_i in range(total_frames):
        collapsed_count = max(0, frame_i - 1)

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.set_xlim(-4, 4)
        ax.set_ylim(-4, 4)
        ax.set_aspect("equal")
        ax.set_facecolor("#0d0d1a")
        fig.patch.set_facecolor("#0d0d1a")
        ax.axis("off")

        for j, unit in enumerate(units):
            is_collapsed = j < collapsed_count
            pts = positions[unit["id"]]

            if is_collapsed:
                # Collapsed: single point near origin
                ax.scatter(0, 0, s=60, color="#44FF88", alpha=0.7, zorder=3)
            else:
                # Open: scattered possibilities
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                ax.scatter(xs, ys, s=40, color="#FF6666", alpha=0.5, zorder=2)
                # Label the ambiguity near centroid
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                ax.text(cx, cy + 0.25, unit["label"][:25],
                        color="white", fontsize=6, ha="center", alpha=0.8)

        open_count = len(units) - collapsed_count
        title = (
            f"Interpretation Space  |  Open: {open_count}  Collapsed: {collapsed_count}"
        )
        ax.set_title(title, color="white", fontsize=10, pad=10)

        legend = [
            mpatches.Patch(color="#FF6666", label="open ambiguity"),
            mpatches.Patch(color="#44FF88", label="resolved"),
        ]
        ax.legend(handles=legend, loc="lower right", fontsize=8,
                  facecolor="#1a1a2e", labelcolor="white")

        frame_path = FRAMES_DIR / f"frame_{frame_i:03d}.png"
        plt.savefig(frame_path, dpi=120, facecolor=fig.get_facecolor())
        plt.close()

    # Compile to video
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", str(FRAMES_DIR / "frame_%03d.png"),
            "-vf", "scale=1200:960",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(OUT_VIDEO),
        ], check=True, capture_output=True)
        print(f"Saved: {OUT_VIDEO}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"ffmpeg unavailable — frames saved to {FRAMES_DIR}/")


if __name__ == "__main__":
    main()
