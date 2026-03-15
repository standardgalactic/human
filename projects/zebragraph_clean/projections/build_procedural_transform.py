#!/usr/bin/env python3
"""build_procedural_transform.py — project canonical graph as ordered operations / state machine.

Usage:
    python3 projections/build_procedural_transform.py data/canonical/essay/graph.json
"""

import json
import sys
from pathlib import Path


def main() -> None:
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    transformations = graph.get("transformations", [])
    events = sorted(
        graph.get("events", []),
        key=lambda e: (e.get("time_order") is None, e.get("time_order", 10**9)),
    )

    steps = []

    # Transformations are the most explicit operations
    for trn in transformations:
        steps.append({
            "step_type": "transformation",
            "id": trn["id"],
            "operation": trn.get("operation", ""),
            "input": trn.get("input", ""),
            "output": trn.get("output", ""),
            "triggered_by": trn.get("triggered_by", []),
            "constraints": [],
            "textual_basis": trn.get("textual_basis", []),
        })

    # Events can also be read as state-change operations
    for evt in events:
        steps.append({
            "step_type": "event",
            "id": evt["id"],
            "operation": evt["label"],
            "input": "",
            "output": "",
            "triggered_by": evt.get("causes", []),
            "constraints": [],
            "textual_basis": evt.get("textual_basis", []),
        })

    out = {
        "category": "procedural_transform",
        "total_steps": len(steps),
        "steps": steps,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
