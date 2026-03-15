#!/usr/bin/env python3
"""render_constraint_dynamics.py — animate activation spreading through the constraint graph.

Takes the canonical graph directly and runs the constraint simulator inline,
then renders each step as a frame showing node activation levels.

Requires: matplotlib networkx

Usage:
    python3 render/render_constraint_dynamics.py data/canonical/essay/graph.json
"""

import json
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import networkx as nx

FRAMES_DIR = Path("data/frames/constraint_dynamics")
OUT_VIDEO   = Path("data/videos/constraint_dynamics.mp4")
FPS = 2


def run_simulator(graph_path: str) -> dict:
    """Import and run the constraint simulator as a module."""
    import importlib.util, os
    spec = importlib.util.spec_from_file_location(
        "constraint_simulator",
        os.path.join(os.path.dirname(__file__), "..", "src", "constraint_simulator.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    # Redirect stdout capture
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        spec.loader.exec_module(mod)
        # Monkey-patch sys.argv and call main
        old_argv = sys.argv[:]
        sys.argv = ["constraint_simulator.py", graph_path]
        try:
            mod.main()
        finally:
            sys.argv = old_argv
    return json.loads(buf.getvalue())


def build_graph(graph: dict) -> nx.DiGraph:
    G = nx.DiGraph()
    for node_type in ("entities", "events", "claims", "ambiguities", "themes", "transformations"):
        for n in graph.get(node_type, []):
            G.add_node(n["id"],
                       label=(n.get("name") or n.get("label") or n.get("text", ""))[:25],
                       ntype=node_type[:-1])  # strip trailing 's'
    for r in graph.get("relations", []):
        G.add_edge(r["source"], r["target"])
    return G


def main() -> None:
    graph_path = sys.argv[1]
    graph = json.loads(Path(graph_path).read_text(encoding="utf-8"))

    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    OUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)

    sim = run_simulator(graph_path)
    steps = sim.get("simulation", [])

    if not steps:
        print("WARNING: empty simulation")
        return

    G = build_graph(graph)
    if len(G.nodes) == 0:
        print("WARNING: empty graph")
        return

    pos = nx.spring_layout(G, seed=42, k=2.0)
    labels = {n: G.nodes[n]["label"] for n in G.nodes}

    norm = plt.Normalize(0, 1)
    colormap = cm.plasma

    for frame_i, step in enumerate(steps):
        state = step.get("state", {})

        node_colors = []
        for n in G.nodes:
            node_state = state.get(n, {})
            activation = node_state.get("activation", 0.0)
            node_colors.append(colormap(norm(min(1.0, activation))))

        fig, axes = plt.subplots(1, 2, figsize=(14, 7),
                                  gridspec_kw={"width_ratios": [3, 1]})
        fig.patch.set_facecolor("#0d0d1a")

        ax = axes[0]
        ax.set_facecolor("#0d0d1a")
        ax.axis("off")

        nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                               node_size=600, ax=ax)
        nx.draw_networkx_labels(G, pos, labels=labels,
                                font_size=6, font_color="white", ax=ax)
        nx.draw_networkx_edges(G, pos, edge_color="#555577",
                               arrows=True, arrowsize=12, ax=ax)

        event_label = step.get("event", "")[:50]
        ax.set_title(f"Step {step['step']}: {event_label}",
                     color="white", fontsize=9)

        # Summary panel
        ax2 = axes[1]
        ax2.set_facecolor("#0d0d1a")
        ax2.axis("off")
        summary = sim.get("summary", [])
        if frame_i < len(summary):
            s = summary[frame_i]
            lines = [
                f"Step {s['step']}",
                f"Avg activation: {s['avg_activation']}",
                f"Amb open: {s['ambiguities_open']}",
                f"Amb resolved: {s['ambiguities_collapsed']}",
            ]
            ax2.text(0.1, 0.7, "\n".join(lines), color="white",
                     fontsize=8, transform=ax2.transAxes, va="top",
                     family="monospace")

        # Colorbar
        sm = cm.ScalarMappable(cmap=colormap, norm=norm)
        sm.set_array([])
        fig.colorbar(sm, ax=ax, orientation="horizontal",
                     fraction=0.04, pad=0.02, label="activation")

        frame_path = FRAMES_DIR / f"frame_{frame_i:03d}.png"
        plt.savefig(frame_path, dpi=120, facecolor=fig.get_facecolor())
        plt.close()

    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", str(FRAMES_DIR / "frame_%03d.png"),
            "-vf", "scale=1680:840",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(OUT_VIDEO),
        ], check=True, capture_output=True)
        print(f"Saved: {OUT_VIDEO}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"ffmpeg unavailable — frames saved to {FRAMES_DIR}/")


if __name__ == "__main__":
    main()
