#!/usr/bin/env python3
"""
Render concept map projection as a clustered network image.
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
    import matplotlib.patches as mpatches
except ImportError:
    print("Missing dependencies: pip install networkx matplotlib")
    raise


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path("videos").mkdir(exist_ok=True)

    G = nx.Graph()

    type_colors = {
        "theme": "#ffdd88",
        "claim": "#ff88cc",
        "entity": "#88ddff"
    }

    for c in data.get("concepts", []):
        G.add_node(c["id"], label=c.get("label", "")[:30], ctype=c.get("type", "entity"))

    for conn in data.get("connections", []):
        src = conn.get("source", "")
        tgt = conn.get("target", "")
        if src and tgt and src in G.nodes and tgt in G.nodes:
            G.add_edge(src, tgt, label=conn.get("relation", ""))

    if len(G.nodes) == 0:
        print("No concepts to render.")
        return

    fig, ax = plt.subplots(figsize=(16, 10))
    fig.patch.set_facecolor("#0a0a0f")
    ax.set_facecolor("#0a0a0f")

    pos = nx.spring_layout(G, k=3.0, seed=42)

    node_colors = [
        type_colors.get(G.nodes[n].get("ctype", "entity"), "#aaaaaa")
        for n in G.nodes
    ]

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=700, ax=ax)
    nx.draw_networkx_labels(
        G, pos,
        labels={n: G.nodes[n].get("label", n)[:20] for n in G.nodes},
        font_size=8, font_color="white", ax=ax
    )
    nx.draw_networkx_edges(G, pos, edge_color="#336633", alpha=0.7, ax=ax)

    legend_handles = [
        mpatches.Patch(color=v, label=k) for k, v in type_colors.items()
    ]
    ax.legend(handles=legend_handles, facecolor="#0a0a0f", labelcolor="white",
              loc="lower right", fontsize=8)

    ax.axis("off")
    plt.tight_layout()
    plt.savefig("videos/concept_map.png", dpi=150, facecolor="#0a0a0f")
    plt.close()
    print("Rendered: videos/concept_map.png")


if __name__ == "__main__":
    main()
