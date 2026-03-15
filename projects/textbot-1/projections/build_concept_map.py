#!/usr/bin/env python3
"""
Derive concept map projection from canonical graph.
Themes become clusters. Claims and entities become concept nodes.
"""

import json
import sys
from pathlib import Path


def main():
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    concepts = []
    seen = set()

    for t in graph.get("themes", []):
        if t["label"] not in seen:
            concepts.append({
                "id": t["id"],
                "label": t["label"],
                "type": "theme",
                "explicit_textual_basis": t.get("textual_basis", [])
            })
            seen.add(t["label"])

    for cl in graph.get("claims", []):
        if cl["text"] not in seen:
            concepts.append({
                "id": cl["id"],
                "label": cl["text"],
                "type": "claim",
                "explicit_textual_basis": cl.get("textual_basis", [])
            })
            seen.add(cl["text"])

    for ent in graph.get("entities", []):
        if ent["name"] not in seen:
            concepts.append({
                "id": ent["id"],
                "label": ent["name"],
                "type": "entity",
                "explicit_textual_basis": ent.get("textual_basis", [])
            })
            seen.add(ent["name"])

    clusters = []
    for t in graph.get("themes", []):
        clusters.append({
            "id": t["id"],
            "label": t["label"],
            "members": t.get("members", [])
        })

    connections = []
    for r in graph.get("relations", []):
        connections.append({
            "source": r.get("source", ""),
            "relation": r.get("relation", ""),
            "target": r.get("target", ""),
            "explicit_textual_basis": r.get("textual_basis", [])
        })

    out = {
        "category": "concept_map",
        "concepts": concepts,
        "clusters": clusters,
        "connections": connections,
        "notes": []
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
