#!/usr/bin/env python3
"""render_diagrammatic_structure.py — draw the typed constraint graph as a static PNG.

Requires: networkx matplotlib

Usage:
    python3 render/render_diagrammatic_structure.py data/projections/essay/diagrammatic_structure.json
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

TYPE_COLORS = {
    "entity":         "#4A90D9",
    "event":          "#E8A838",
    "claim":          "#7BC67E",
    "ambiguity":      "#E05C5C",
    "transformation": "#B07BE8",
}
DEFAULT_COLOR = "#AAAAAA"

def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path("data/videos").mkdir(parents=True, exist_ok=True)

    G = nx.DiGraph()

    for node in data["nodes"]:
        G.add_node(node["id"], label=node["label"][:30], ntype=node.get("type", ""))

    for edge in data["edges"]:
        G.add_edge(edge["source"], edge["target"], label=edge.get("label", ""))

    if len(G.nodes) == 0:
        print("WARNING: no nodes to render")
        return

    pos = nx.spring_layout(G, seed=42, k=2.5)

    node_colors = [
        TYPE_COLORS.get(G.nodes[n].get("ntype", ""), DEFAULT_COLOR)
        for n in G.nodes
    ]
    labels = {n: G.nodes[n]["label"] for n in G.nodes}

    fig, ax = plt.subplots(figsize=(16, 10))
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=800, ax=ax)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=7, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color="#555555", arrows=True,
                           arrowsize=15, ax=ax, connectionstyle="arc3,rad=0.1")
    edge_labels = {(e["source"], e["target"]): e.get("label", "")[:15]
                   for e in data["edges"]}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=6, ax=ax)

    # Legend
    from matplotlib.patches import Patch
    legend = [Patch(color=c, label=t) for t, c in TYPE_COLORS.items()]
    ax.legend(handles=legend, loc="upper left", fontsize=8)

    ax.set_title("Diagrammatic Structure", fontsize=14)
    ax.axis("off")
    plt.tight_layout()

    out = "data/videos/diagrammatic_structure.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
