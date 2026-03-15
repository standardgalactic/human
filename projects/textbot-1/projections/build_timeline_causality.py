#!/usr/bin/env python3
"""
Derive timeline causality projection from canonical graph.
Events ordered by time_order. Causal edges become causal_chains.
"""

import json
import sys
from pathlib import Path


def main():
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    events = sorted(
        graph.get("events", []),
        key=lambda e: (e.get("time_order") is None, e.get("time_order", 10**9))
    )

    # Build lookup
    event_index = {ev["id"]: ev for ev in graph.get("events", [])}

    timeline = []
    for i, ev in enumerate(events):
        timeline.append({
            "index": i + 1,
            "event_id": ev.get("id", ""),
            "label": ev.get("label", ""),
            "temporal_marker": "",
            "cause": ", ".join(ev.get("causes", [])),
            "effect": ", ".join(ev.get("effects", [])),
            "participants": ev.get("participants", []),
            "explicit_textual_basis": ev.get("textual_basis", [])
        })

    # Build causal chains from relations of type 'causes'
    causal_edges = [
        r for r in graph.get("relations", [])
        if r.get("relation") == "causes"
    ]

    chains = []
    for i, edge in enumerate(causal_edges):
        chains.append({
            "chain_id": f"chain_{i:03d}",
            "steps": [edge.get("source", ""), edge.get("target", "")]
        })

    out = {
        "category": "timeline_causality",
        "timeline": timeline,
        "causal_chains": chains,
        "reversals": [],
        "delayed_revelations": [],
        "notes": []
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
