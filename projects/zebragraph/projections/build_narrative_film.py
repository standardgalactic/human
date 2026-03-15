#!/usr/bin/env python3
"""build_narrative_film.py — project canonical graph into cinematic scene list.

Usage:
    python3 projections/build_narrative_film.py data/canonical/essay/graph.json
"""

import json
import sys
from pathlib import Path


def main() -> None:
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    # Index entities and ambiguities for fast lookup
    entities_by_id = {e["id"]: e for e in graph.get("entities", [])}
    ambiguities_by_participant: dict[str, list[str]] = {}
    for amb in graph.get("ambiguities", []):
        for pid in amb.get("applies_to", []):
            ambiguities_by_participant.setdefault(pid, []).append(amb["label"])

    events = sorted(
        graph.get("events", []),
        key=lambda e: (e.get("time_order") is None, e.get("time_order", 10**9)),
    )

    scenes = []
    for evt in events:
        participants = evt.get("participants", [])
        character_names = [
            entities_by_id[p]["name"] if p in entities_by_id else p
            for p in participants
        ]
        uncertain = []
        for p in participants:
            uncertain.extend(ambiguities_by_participant.get(p, []))

        scenes.append({
            "scene_id": evt["id"],
            "summary": evt["label"],
            "characters": character_names,
            "location": "",
            "actions": [evt["label"]],
            "effects": evt.get("effects", []),
            "dialogue_candidates": [],
            "uncertain_details": list(dict.fromkeys(uncertain)),
            "textual_basis": evt.get("textual_basis", []),
        })

    out = {
        "category": "narrative_film",
        "total_scenes": len(scenes),
        "global_style_notes": [],
        "scenes": scenes,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
