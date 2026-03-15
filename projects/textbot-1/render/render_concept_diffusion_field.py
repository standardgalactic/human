#!/usr/bin/env python3
"""
Render concept diffusion field as an animated mp4.
Embeds concepts via sentence-transformers, reduces to 2D via PCA,
and animates progressive addition of concepts — simulating semantic
field convergence as the text is read.

Requires: sentence-transformers, scikit-learn, matplotlib, ffmpeg
Falls back to random layout if sentence-transformers is unavailable.
"""

import json
import sys
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


def embed_random(concepts, seed=42):
    rng = np.random.RandomState(seed)
    return rng.randn(len(concepts), 2)


def embed_with_transformers(concepts):
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.decomposition import PCA
        model = SentenceTransformer("all-MiniLM-L6-v2")
        vecs = model.encode(concepts)
        if vecs.shape[0] >= 2:
            pca = PCA(n_components=2)
            return pca.fit_transform(vecs)
        return vecs[:, :2]
    except Exception as e:
        print(f"Transformer embedding unavailable ({e}), using random layout.")
        return embed_random(concepts)


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path("videos").mkdir(exist_ok=True)

    # Gather concept labels from all node types
    concepts = []
    for node in data.get("nodes", []):
        label = node.get("label", "")
        if label:
            concepts.append(label[:60])

    if not concepts:
        # Fallback: try top-level concepts key
        for c in data.get("concepts", []):
            label = c.get("label", "")
            if label:
                concepts.append(label[:60])

    if not concepts:
        print("No concepts to embed.")
        return

    print(f"Embedding {len(concepts)} concepts...")
    points = embed_with_transformers(concepts)

    # Normalize to [0.1, 0.9]
    for dim in range(points.shape[1]):
        mn, mx = points[:, dim].min(), points[:, dim].max()
        rng = mx - mn if mx != mn else 1.0
        points[:, dim] = 0.1 + 0.8 * (points[:, dim] - mn) / rng

    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(1, len(concepts) + 1):
            subset_pts = points[:i]
            subset_labels = concepts[:i]

            fig, ax = plt.subplots(figsize=(12, 8))
            fig.patch.set_facecolor("#0a0a0f")
            ax.set_facecolor("#0a0a0f")

            # Draw all final positions faintly
            ax.scatter(points[:, 0], points[:, 1], s=30, color="#1a3a1a", zorder=1)

            # Draw revealed concepts
            ax.scatter(subset_pts[:, 0], subset_pts[:, 1],
                       s=120, color="#00ff88", alpha=0.85, zorder=3)

            for j, (px, py) in enumerate(subset_pts):
                ax.text(px, py + 0.025, subset_labels[j][:28],
                        color="#aaffcc", fontsize=7, ha="center", va="bottom")

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            ax.set_title(
                f"Concept Diffusion Field  [{i}/{len(concepts)}]",
                color="#88ffaa", fontsize=11
            )

            plt.tight_layout()
            plt.savefig(f"{tmpdir}/frame_{i:04d}.png", dpi=120, facecolor="#0a0a0f")
            plt.close()

        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", "3",
            "-i", f"{tmpdir}/frame_%04d.png",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "videos/concept_diffusion_field.mp4"
        ], check=False)
        print("Rendered: videos/concept_diffusion_field.mp4")


if __name__ == "__main__":
    main()
