#!/usr/bin/env python3
"""build_sonic_mapping.py — project canonical graph into acoustic/musical parameters.

Semantic tension (ambiguity density relative to events) drives tempo and texture.
Claim density drives harmonic complexity. Timeline position drives overall arc.

Usage:
    python3 projections/build_sonic_mapping.py data/canonical/essay/graph.json
"""

import json
import sys
import math
from pathlib import Path


def tension(amb_count: int, evt_count: int) -> float:
    if evt_count == 0:
        return 0.5
    return min(1.0, amb_count / max(1, evt_count))


def tempo_from_tension(t: float) -> int:
    # Low tension → slow (50 bpm); high tension → fast (140 bpm)
    return int(50 + 90 * t)


def texture_from_tension(t: float) -> str:
    if t < 0.3:
        return "sparse"
    if t < 0.6:
        return "mid"
    return "dense"


def pitch_class(index: int, total: int) -> str:
    # Map position in narrative to a harmonic progression
    ratio = index / max(1, total - 1)
    classes = ["I", "II", "III", "IV", "V", "VI", "VII"]
    return classes[int(ratio * (len(classes) - 1))]


def main() -> None:
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    events = sorted(
        graph.get("events", []),
        key=lambda e: (e.get("time_order") is None, e.get("time_order", 10**9)),
    )
    ambiguities = graph.get("ambiguities", [])
    claims = graph.get("claims", [])

    total_events = len(events)
    total_amb = len(ambiguities)
    total_claims = len(claims)

    base_tension = tension(total_amb, total_events)

    segments = []
    for i, evt in enumerate(events):
        # Local tension: open ambiguities that apply to participants of this event
        participant_ids = set(evt.get("participants", []))
        local_open_amb = sum(
            1 for a in ambiguities
            if a.get("status", "open") == "open"
            and set(a.get("applies_to", [])) & participant_ids
        )
        local_tension = tension(local_open_amb + 1, total_events)
        arc_position = i / max(1, total_events - 1)  # 0.0 → 1.0

        # Envelope: rise to midpoint, resolve toward end
        envelope = math.sin(math.pi * arc_position)

        segments.append({
            "index": i + 1,
            "event": evt["label"],
            "event_id": evt["id"],
            "tempo_bpm": tempo_from_tension(local_tension * envelope + base_tension * 0.3),
            "texture": texture_from_tension(local_tension),
            "harmonic_position": pitch_class(i, total_events),
            "intensity": round(local_tension * envelope, 3),
            "arc_position": round(arc_position, 3),
            "open_ambiguities_at_step": local_open_amb,
        })

    # Overall arc shape
    arc = "rising" if total_events < 3 else (
        "arch" if segments[len(segments)//2]["intensity"] > segments[-1]["intensity"]
        else "cumulative"
    )

    out = {
        "category": "sonic_mapping",
        "total_segments": len(segments),
        "base_tension": round(base_tension, 3),
        "arc_shape": arc,
        "suggested_instrumentation": (
            "sparse strings" if base_tension < 0.3
            else "chamber ensemble" if base_tension < 0.6
            else "full orchestra with dissonance"
        ),
        "segments": segments,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
