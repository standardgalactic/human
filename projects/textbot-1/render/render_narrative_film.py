#!/usr/bin/env python3
"""
Render narrative film projection as a storyboard image sequence compiled to mp4.
Requires: ImageMagick (convert), ffmpeg
"""

import json
import sys
import subprocess
import tempfile
from pathlib import Path


def wrap_text(text, width=40):
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
    return "\n".join(lines)


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path("videos").mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        frames = []
        for i, scene in enumerate(data.get("scenes", [])):
            text = wrap_text(f"SCENE {i+1}\n\n{scene.get('summary','')}")
            frame = f"{tmpdir}/frame_{i:04d}.png"
            subprocess.run([
                "convert",
                "-size", "1280x720",
                "xc:#0a0a0f",
                "-fill", "#88ffaa",
                "-font", "DejaVu-Sans-Mono",
                "-pointsize", "32",
                "-gravity", "Center",
                f"label:{text}",
                frame
            ], check=False)
            frames.append(frame)

        if frames:
            subprocess.run([
                "ffmpeg", "-y",
                "-framerate", "1",
                "-i", f"{tmpdir}/frame_%04d.png",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "videos/narrative_film.mp4"
            ], check=False)
            print("Rendered: videos/narrative_film.mp4")
        else:
            print("No scenes to render.")


if __name__ == "__main__":
    main()
