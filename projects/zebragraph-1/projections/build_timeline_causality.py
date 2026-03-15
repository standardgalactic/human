#!/usr/bin/env python3
"""build_timeline_causality.py — project canonical graph into causal event timeline.

Usage:
    python3 projections/build_timeline_causality.py data/canonical/essay/graph.json
"""

import json
import sys
from pathlib import Path


def main() -> None:
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    events_by_id = {e["id"]: e for e in graph.get("events", [])}

    timeline_refs = graph.get("timeline", [])
    ordered_ids = [t["event_id"] for t in timeline_refs if "event_id" in t]

    # Fill in any events not in timeline
    for eid in events_by_id:
        if eid not in ordered_ids:
            ordered_ids.append(eid)

    entries = []
    for i, eid in enumerate(ordered_ids):
        if eid not in events_by_id:
            continue
        evt = events_by_id[eid]
        causes_labels = [
            events_by_id[c]["label"] if c in events_by_id else c
            for c in evt.get("causes", [])
        ]
        effects_labels = [
            events_by_id[e]["label"] if e in events_by_id else e
            for e in evt.get("effects", [])
        ]
        entries.append({
            "index": i + 1,
            "event_id": eid,
            "event": evt["label"],
            "participants": evt.get("participants", []),
            "causes": causes_labels,
            "effects": effects_labels,
            "textual_basis": evt.get("textual_basis", []),
        })

    out = {
        "category": "timeline_causality",
        "total_events": len(entries),
        "timeline": entries,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
