#!/usr/bin/env python3
"""build_diagrammatic_structure.py — project canonical graph into typed node/edge diagram.

Usage:
    python3 projections/build_diagrammatic_structure.py data/canonical/essay/graph.json
"""

import json
import sys
from pathlib import Path


def main() -> None:
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    nodes = []

    for e in graph.get("entities", []):
        nodes.append({"id": e["id"], "label": e["name"], "type": "entity"})

    for ev in graph.get("events", []):
        nodes.append({"id": ev["id"], "label": ev["label"], "type": "event"})

    for cl in graph.get("claims", []):
        nodes.append({"id": cl["id"], "label": cl["text"][:80], "type": "claim"})

    for amb in graph.get("ambiguities", []):
        nodes.append({
            "id": amb["id"],
            "label": amb["label"],
            "type": "ambiguity",
            "status": amb.get("status", "open"),
        })

    for trn in graph.get("transformations", []):
        nodes.append({
            "id": trn["id"],
            "label": f"{trn.get('input','')} → {trn.get('output','')}",
            "type": "transformation",
        })

    edges = []
    for r in graph.get("relations", []):
        edges.append({
            "source": r["source"],
            "target": r["target"],
            "label": r.get("relation", r.get("type", "")),
        })

    clusters = [
        {"id": t["id"], "label": t["label"], "members": t.get("members", [])}
        for t in graph.get("themes", [])
    ]

    out = {
        "category": "diagrammatic_structure",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
