#!/usr/bin/env python3
"""
Render diagrammatic structure projection as a network graph image.
Requires: networkx, matplotlib
"""

import json
import sys
from pathlib import Path

try:
    import networkx as nx
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("Missing dependencies: pip install networkx matplotlib")
    raise


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path("videos").mkdir(exist_ok=True)

    G = nx.DiGraph()

    type_colors = {
        "entity": "#88ddff",
        "event": "#ffdd88",
        "claim": "#ff88cc",
        "ambiguity": "#ff6666",
        "concept": "#aaffaa"
    }

    for n in data.get("nodes", []):
        G.add_node(n["id"], label=n.get("label", n["id"])[:30], ntype=n.get("type", "entity"))

    for e in data.get("edges", []):
        src = e.get("source", "")
        tgt = e.get("target", "")
        if src and tgt:
            G.add_edge(src, tgt, label=e.get("relation", ""))

    if len(G.nodes) == 0:
        print("No nodes to render.")
        return

    fig, ax = plt.subplots(figsize=(16, 10))
    fig.patch.set_facecolor("#0a0a0f")
    ax.set_facecolor("#0a0a0f")

    pos = nx.spring_layout(G, k=2.5, seed=42)

    node_colors = [
        type_colors.get(G.nodes[n].get("ntype", "entity"), "#aaaaaa")
        for n in G.nodes
    ]

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=800, ax=ax)
    nx.draw_networkx_labels(
        G, pos,
        labels={n: G.nodes[n].get("label", n)[:20] for n in G.nodes},
        font_size=8, font_color="white", ax=ax
    )
    nx.draw_networkx_edges(G, pos, edge_color="#446644", arrows=True, ax=ax)
    edge_labels = nx.get_edge_attributes(G, "label")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7, font_color="#88ffaa", ax=ax)

    ax.axis("off")
    plt.tight_layout()
    plt.savefig("videos/diagrammatic_structure.png", dpi=150, facecolor="#0a0a0f")
    plt.close()
    print("Rendered: videos/diagrammatic_structure.png")


if __name__ == "__main__":
    main()
