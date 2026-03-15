#!/usr/bin/env python3
"""render_concept_diffusion.py — animate semantic field convergence.

Concepts start dispersed; as the narrative progresses they cluster.
Uses PCA over sentence-transformer embeddings when available;
falls back to deterministic random layout otherwise.

Requires: matplotlib
Optional: sentence-transformers scikit-learn  (for real embeddings)

Usage:
    python3 render/render_concept_diffusion.py data/projections/essay/concept_map.json
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

FRAMES_DIR = Path("data/frames/concept_diffusion")
OUT_VIDEO   = Path("data/videos/concept_diffusion.mp4")
FPS = 2
SEED = 7


def fake_embed(concepts: list[str], seed: int) -> list[tuple[float, float]]:
    """Deterministic pseudo-layout when sentence-transformers not available."""
    rng = random.Random(seed)
    return [(rng.uniform(-3, 3), rng.uniform(-3, 3)) for _ in concepts]


def real_embed(concepts: list[str]) -> list[tuple[float, float]]:
    from sentence_transformers import SentenceTransformer
    from sklearn.decomposition import PCA
    model = SentenceTransformer("all-MiniLM-L6-v2")
    vecs = model.encode(concepts)
    pts = PCA(n_components=2).fit_transform(vecs)
    return [(float(p[0]), float(p[1])) for p in pts]


def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    OUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)

    # Collect all concept labels from clusters
    concepts = []
    cluster_map: dict[str, str] = {}  # concept → cluster label

    for cluster in data.get("clusters", []):
        for member in cluster.get("members", []):
            if member not in concepts:
                concepts.append(member)
            cluster_map[member] = cluster["label"]

    if not concepts:
        print("WARNING: no concepts to render")
        return

    # Try real embeddings; fall back gracefully
    try:
        points = real_embed(concepts)
        embed_method = "sentence-transformers"
    except Exception:
        points = fake_embed(concepts, SEED)
        embed_method = "pseudo-random layout"

    print(f"Embedding method: {embed_method}")

    total_frames = len(concepts) + 2
    all_xs = [p[0] for p in points]
    all_ys = [p[1] for p in points]
    margin = 0.5
    xlim = (min(all_xs) - margin, max(all_xs) + margin)
    ylim = (min(all_ys) - margin, max(all_ys) + margin)

    # Unique cluster colours
    cluster_labels = list(dict.fromkeys(cluster_map.values()))
    cmap = plt.cm.get_cmap("tab10", max(1, len(cluster_labels)))
    cluster_colors = {label: cmap(i) for i, label in enumerate(cluster_labels)}

    for frame_i in range(total_frames):
        revealed = max(0, frame_i)

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.set_facecolor("#0d0d1a")
        fig.patch.set_facecolor("#0d0d1a")
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.axis("off")

        for j, (concept, (x, y)) in enumerate(zip(concepts, points)):
            if j >= revealed:
                continue
            color = cluster_colors.get(cluster_map.get(concept, ""), "#AAAAAA")
            ax.scatter(x, y, s=80, color=color, alpha=0.85, zorder=3)
            ax.text(x, y + 0.12, concept[:22], color="white",
                    fontsize=7, ha="center", alpha=0.9)

        ax.set_title(
            f"Concept Field  |  Revealed: {revealed}/{len(concepts)}",
            color="white", fontsize=10, pad=10,
        )

        frame_path = FRAMES_DIR / f"frame_{frame_i:03d}.png"
        plt.savefig(frame_path, dpi=120, facecolor=fig.get_facecolor())
        plt.close()

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
