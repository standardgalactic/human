#!/usr/bin/env python3
"""
Derive character state projection from canonical graph.
Each entity becomes a character with initial and evolving state.
State changes are inferred from events the entity participates in.
"""

import json
import sys
from pathlib import Path


def main():
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    events_by_participant = {}
    for ev in graph.get("events", []):
        for p in ev.get("participants", []):
            events_by_participant.setdefault(p, []).append(ev)

    ambiguities_by_entity = {}
    for amb in graph.get("ambiguities", []):
        for ref in amb.get("applies_to", []):
            ambiguities_by_entity.setdefault(ref, []).append(amb)

    characters = []
    for ent in graph.get("entities", []):
        eid = ent["id"]

        explicit_attrs = ent.get("attributes", {}).get("explicit", [])
        uncertain_attrs = ent.get("attributes", {}).get("uncertain", [])

        # Supplement uncertain from ambiguities
        for amb in ambiguities_by_entity.get(eid, []):
            if amb["label"] not in uncertain_attrs:
                uncertain_attrs.append(amb["label"])

        state_changes = []
        for ev in events_by_participant.get(eid, []):
            state_changes.append({
                "trigger": ev.get("label", ""),
                "attribute": "participation",
                "before": "absent",
                "after": "active",
                "explicit_textual_basis": ev.get("textual_basis", [])
            })

        characters.append({
            "id": eid,
            "name": ent["name"],
            "initial_state": {
                "explicit_attributes": explicit_attrs,
                "uncertain_attributes": uncertain_attrs
            },
            "state_changes": state_changes,
            "final_state": {
                "explicit_attributes": explicit_attrs,
                "uncertain_attributes": uncertain_attrs
            }
        })

    out = {
        "category": "character_state",
        "characters": characters,
        "notes": []
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
