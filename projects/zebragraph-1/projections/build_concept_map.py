#!/usr/bin/env python3
"""build_concept_map.py — project canonical graph into thematic concept clusters.

Usage:
    python3 projections/build_concept_map.py data/canonical/essay/graph.json
"""

import json
import sys
from pathlib import Path


def main() -> None:
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    entities_by_id = {e["id"]: e["name"] for e in graph.get("entities", [])}
    claims_by_id   = {c["id"]: c["text"][:60] for c in graph.get("claims", [])}
    events_by_id   = {e["id"]: e["label"] for e in graph.get("events", [])}

    def resolve_label(nid: str) -> str:
        return (
            entities_by_id.get(nid)
            or claims_by_id.get(nid)
            or events_by_id.get(nid)
            or nid
        )

    themes = graph.get("themes", [])
    clusters = []
    for thm in themes:
        members = thm.get("members", [])
        clusters.append({
            "id": thm["id"],
            "label": thm["label"],
            "member_count": len(members),
            "members": [resolve_label(m) for m in members],
            "textual_basis": thm.get("textual_basis", []),
        })

    # Connections between clusters via shared members
    connections = []
    for i, a in enumerate(themes):
        for b in themes[i + 1:]:
            shared = set(a.get("members", [])) & set(b.get("members", []))
            if shared:
                connections.append({
                    "from": a["id"],
                    "to": b["id"],
                    "shared_members": list(shared),
                })

    out = {
        "category": "concept_map",
        "total_clusters": len(clusters),
        "clusters": clusters,
        "connections": connections,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
