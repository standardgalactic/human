#!/usr/bin/env python3
"""
Derive diagrammatic structure projection from canonical graph.
Entities, events, and claims become typed nodes.
Relations become typed edges.
Themes become clusters.
"""

import json
import sys
from pathlib import Path


def main():
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    nodes = []

    for e in graph.get("entities", []):
        nodes.append({
            "id": e["id"],
            "label": e["name"],
            "type": "entity",
            "explicit_textual_basis": e.get("textual_basis", [])
        })

    for ev in graph.get("events", []):
        nodes.append({
            "id": ev["id"],
            "label": ev["label"],
            "type": "event",
            "explicit_textual_basis": ev.get("textual_basis", [])
        })

    for cl in graph.get("claims", []):
        nodes.append({
            "id": cl["id"],
            "label": cl["text"],
            "type": "claim",
            "explicit_textual_basis": cl.get("textual_basis", [])
        })

    for amb in graph.get("ambiguities", []):
        nodes.append({
            "id": amb["id"],
            "label": amb["label"],
            "type": "ambiguity",
            "explicit_textual_basis": amb.get("textual_basis", [])
        })

    edges = []
    for r in graph.get("relations", []):
        edges.append({
            "source": r.get("source", ""),
            "relation": r.get("relation", ""),
            "target": r.get("target", ""),
            "explicit_textual_basis": r.get("textual_basis", [])
        })

    clusters = []
    for t in graph.get("themes", []):
        clusters.append({
            "label": t["label"],
            "members": t.get("members", [])
        })

    out = {
        "category": "diagrammatic_structure",
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters,
        "transformations": graph.get("transformations", []),
        "notes": []
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
