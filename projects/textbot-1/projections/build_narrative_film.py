#!/usr/bin/env python3
"""
Derive narrative film projection from canonical graph.
Events ordered by time_order become scenes.
Ambiguities attached to participants become uncertain_details.
"""

import json
import sys
from pathlib import Path


def main():
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    ambiguity_index = {}
    for amb in graph.get("ambiguities", []):
        for ref in amb.get("applies_to", []):
            ambiguity_index.setdefault(ref, []).append(amb["label"])

    events = sorted(
        graph.get("events", []),
        key=lambda e: (e.get("time_order") is None, e.get("time_order", 10**9))
    )

    scenes = []
    for event in events:
        participants = event.get("participants", [])
        uncertain = []
        for p in participants:
            uncertain.extend(ambiguity_index.get(p, []))

        scenes.append({
            "scene_id": event.get("id", ""),
            "summary": event.get("label", ""),
            "characters": participants,
            "location": "",
            "actions": [event.get("label", "")],
            "dialogue_candidates": [],
            "visual_requirements": [],
            "uncertain_details": uncertain,
            "explicit_textual_basis": event.get("textual_basis", [])
        })

    out = {
        "category": "narrative_film",
        "scenes": scenes,
        "global_style_notes": [],
        "notes": []
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
