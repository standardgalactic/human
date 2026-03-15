#!/usr/bin/env python3
"""build_character_state.py — project entities as state vectors evolving under narrative constraints.

Usage:
    python3 projections/build_character_state.py data/canonical/essay/graph.json
"""

import json
import sys
from pathlib import Path


def main() -> None:
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    events = sorted(
        graph.get("events", []),
        key=lambda e: (e.get("time_order") is None, e.get("time_order", 10**9)),
    )

    # Only track person/character entities
    characters = [
        e for e in graph.get("entities", [])
        if e.get("type", "").lower() in ("person", "character", "agent", "entity", "")
    ]

    relations = graph.get("relations", [])

    character_records = []
    for char in characters:
        initial = dict(char.get("attributes", {}).get("explicit", []) and {})
        initial["certainty"] = 0.2

        state_changes = []
        for evt in events:
            if char["id"] not in evt.get("participants", []):
                continue
            # Look for ambiguities involving this character that this event resolves
            resolved = []
            for amb in graph.get("ambiguities", []):
                if char["id"] in amb.get("applies_to", []):
                    if evt["id"] in amb.get("resolved_by", []):
                        resolved.append(amb["label"])

            state_changes.append({
                "event_id": evt["id"],
                "event_label": evt["label"],
                "attributes_constrained": resolved,
                "time_order": evt.get("time_order"),
            })

        character_records.append({
            "entity_id": char["id"],
            "name": char["name"],
            "type": char.get("type", ""),
            "initial_state": {
                "explicit_attributes": char.get("attributes", {}).get("explicit", []),
                "uncertain_attributes": char.get("attributes", {}).get("uncertain", []),
            },
            "state_changes": state_changes,
            "final_certainty": min(1.0, 0.2 + 0.1 * len(state_changes)),
        })

    out = {
        "category": "character_state",
        "total_characters": len(character_records),
        "characters": character_records,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
