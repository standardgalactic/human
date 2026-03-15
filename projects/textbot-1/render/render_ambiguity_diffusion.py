#!/usr/bin/env python3
"""
Render ambiguity diffusion projection as an animated mp4.
Each frame shows the interpretation space for one ambiguity unit.
Points scatter when open, converge when collapsed.
Requires: matplotlib, ffmpeg
"""

import json
import sys
import random
import subprocess
import tempfile
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

    units = data.get("units", [])
    if not units:
        print("No units to render.")
        return

    rng = random.Random(42)

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, unit in enumerate(units):
            possibilities = unit.get("possible_interpretations", []) or ["?"]
            collapsed = unit.get("status") == "resolved"
            n = len(possibilities)

            fig, ax = plt.subplots(figsize=(10, 7))
            fig.patch.set_facecolor("#0a0a0f")
            ax.set_facecolor("#0a0a0f")

            if collapsed:
                xs = [0.5]
                ys = [0.5]
                alpha = 0.9
                color = "#00ff88"
                size = 300
            else:
                spread = 0.4
                xs = [0.5 + rng.uniform(-spread, spread) for _ in range(n)]
                ys = [0.5 + rng.uniform(-spread, spread) for _ in range(n)]
                alpha = 0.6
                color = "#ff8844"
                size = 150

            ax.scatter(xs, ys, s=size, c=color, alpha=alpha, zorder=3)

            for j, (x, y) in enumerate(zip(xs, ys)):
                label = possibilities[j] if not collapsed else (possibilities[0] if possibilities else "resolved")
                ax.text(x, y + 0.04, label[:25], color="white", fontsize=9,
                        ha="center", va="bottom")

            status_label = "RESOLVED" if collapsed else f"{n} possibilities"
            ax.set_title(
                f"{unit.get('label','')[:60]}\n{status_label}",
                color="#88ffaa", fontsize=11
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")

            plt.tight_layout()
            plt.savefig(f"{tmpdir}/frame_{i:04d}.png", dpi=120, facecolor="#0a0a0f")
            plt.close()

        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", "2",
            "-i", f"{tmpdir}/frame_%04d.png",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "videos/ambiguity_diffusion.mp4"
        ], check=False)
        print("Rendered: videos/ambiguity_diffusion.mp4")


if __name__ == "__main__":
    main()
