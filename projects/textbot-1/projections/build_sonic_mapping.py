#!/usr/bin/env python3
"""
Derive sonic mapping projection from canonical graph.
Maps ambiguity density, claim density, and event density to acoustic parameters.
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

    total_events = max(1, len(events))
    total_ambiguities = len(graph.get("ambiguities", []))
    total_claims = len(graph.get("claims", []))

    segments = []
    for i, ev in enumerate(events):
        progress = i / total_events

        tension = round(
            0.3
            + 0.4 * (total_ambiguities / max(1, total_events))
            + 0.3 * (1.0 - progress),
            2
        )
        tension = min(1.0, max(0.0, tension))

        if tension > 0.7:
            tempo = "fast"
            texture = "dense"
            dynamics = "loud"
            register = "high"
        elif tension > 0.4:
            tempo = "moderate"
            texture = "layered"
            dynamics = "moderate"
            register = "mid"
        else:
            tempo = "slow"
            texture = "sparse"
            dynamics = "soft"
            register = "low"

        segments.append({
            "segment_id": ev.get("id", f"seg_{i:03d}"),
            "span_summary": ev.get("label", ""),
            "emotion": "neutral",
            "tension": tension,
            "tempo": tempo,
            "texture": texture,
            "pitch_register": register,
            "dynamics": dynamics,
            "suggested_instrumentation": [],
            "explicit_textual_basis": ev.get("textual_basis", [])
        })

    overall_arc = "ascending" if total_ambiguities > total_events / 2 else "stable"

    out = {
        "category": "sonic_mapping",
        "segments": segments,
        "overall_arc": overall_arc,
        "key_transitions": [],
        "notes": []
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
