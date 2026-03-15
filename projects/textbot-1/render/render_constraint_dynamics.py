#!/usr/bin/env python3
"""
Render constraint dynamics simulation as an animated mp4.
Reads the canonical graph directly and runs the constraint simulator.
Node activation spreads across the graph as events are processed.
Requires: networkx, matplotlib, ffmpeg
"""

import json
import sys
import copy
import subprocess
import tempfile
from pathlib import Path

try:
    import networkx as nx
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    import numpy as np
except ImportError:
    print("Missing dependencies: pip install networkx matplotlib numpy")
    raise


def run_simulation(graph):
    state = {}

    for entity in graph.get("entities", []):
        state[entity["id"]] = {
            "type": "entity",
            "label": entity["name"][:20],
            "activation": 0.0,
            "certainty": 0.2
        }
    for amb in graph.get("ambiguities", []):
        state[amb["id"]] = {
            "type": "ambiguity",
            "label": amb["label"][:20],
            "activation": 0.0,
            "collapsed": amb.get("status") == "resolved"
        }
    for cl in graph.get("claims", []):
        state[cl["id"]] = {
            "type": "claim",
            "label": cl["text"][:20],
            "activation": 0.0
        }

    timeline = graph.get("timeline", [])
    history = []

    for step in timeline:
        event_id = step.get("event_id")
        if not event_id:
            continue
        history.append(copy.deepcopy(state))
        for rel in graph.get("relations", []):
            if rel.get("source") == event_id:
                target = rel.get("target")
                if target and target in state:
                    state[target]["activation"] = min(
                        1.0, state[target].get("activation", 0.0) + 0.25
                    )
                    if state[target].get("type") == "ambiguity" and rel.get("relation") == "resolves":
                        state[target]["collapsed"] = True

    history.append(copy.deepcopy(state))
    return history


def main():
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path("videos").mkdir(exist_ok=True)

    history = run_simulation(graph)
    if not history:
        print("No simulation steps to render.")
        return

    # Build graph layout once
    G = nx.DiGraph()
    for nid, ndata in history[0].items():
        G.add_node(nid, label=ndata.get("label", nid), ntype=ndata.get("type", "entity"))
    for rel in graph.get("relations", []):
        src, tgt = rel.get("source", ""), rel.get("target", "")
        if src in G.nodes and tgt in G.nodes:
            G.add_edge(src, tgt)

    if len(G.nodes) == 0:
        print("No nodes in graph.")
        return

    pos = nx.spring_layout(G, k=2.5, seed=42)

    type_base = {"entity": (0.3, 0.7, 1.0), "claim": (1.0, 0.3, 0.7),
                 "ambiguity": (1.0, 0.5, 0.2)}

    with tempfile.TemporaryDirectory() as tmpdir:
        for frame_i, state in enumerate(history):
            fig, ax = plt.subplots(figsize=(14, 9))
            fig.patch.set_facecolor("#0a0a0f")
            ax.set_facecolor("#0a0a0f")

            node_colors = []
            for nid in G.nodes:
                s = state.get(nid, {})
                act = s.get("activation", 0.0)
                base = type_base.get(s.get("type", "entity"), (0.5, 0.5, 0.5))
                color = tuple(min(1.0, b + act * 0.6) for b in base)
                node_colors.append(color)

            nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=600, ax=ax)
            nx.draw_networkx_labels(
                G, pos,
                labels={n: G.nodes[n].get("label", n)[:18] for n in G.nodes},
                font_size=7, font_color="white", ax=ax
            )
            nx.draw_networkx_edges(G, pos, edge_color="#336633", arrows=True,
                                   alpha=0.6, ax=ax)

            ax.set_title(f"Constraint Dynamics — step {frame_i + 1}/{len(history)}",
                         color="#88ffaa", fontsize=11)
            ax.axis("off")
            plt.tight_layout()
            plt.savefig(f"{tmpdir}/frame_{frame_i:04d}.png", dpi=120, facecolor="#0a0a0f")
            plt.close()

        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", "2",
            "-i", f"{tmpdir}/frame_%04d.png",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "videos/constraint_dynamics.mp4"
        ], check=False)
        print("Rendered: videos/constraint_dynamics.mp4")


if __name__ == "__main__":
    main()
