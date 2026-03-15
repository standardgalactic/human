#!/usr/bin/env python3
"""
Derive procedural transform projection from canonical graph.
Transformations become steps. Events provide ordering.
"""

import json
import sys
from pathlib import Path


def main():
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    steps = []

    for i, trn in enumerate(graph.get("transformations", [])):
        steps.append({
            "step_id": trn.get("id", f"step_{i:03d}"),
            "operation": trn.get("operation", ""),
            "input_state": trn.get("input", ""),
            "output_state": trn.get("output", ""),
            "constraints": [],
            "preconditions": [],
            "effects": trn.get("triggered_by", []),
            "explicit_textual_basis": trn.get("textual_basis", [])
        })

    # Supplement with events if transformations are sparse
    if not steps:
        events = sorted(
            graph.get("events", []),
            key=lambda e: (e.get("time_order") is None, e.get("time_order", 10**9))
        )
        for i, ev in enumerate(events):
            steps.append({
                "step_id": ev.get("id", f"step_{i:03d}"),
                "operation": ev.get("label", ""),
                "input_state": "",
                "output_state": "",
                "constraints": [],
                "preconditions": ev.get("causes", []),
                "effects": ev.get("effects", []),
                "explicit_textual_basis": ev.get("textual_basis", [])
            })

    initial = steps[0]["input_state"] if steps else ""
    final = steps[-1]["output_state"] if steps else ""

    out = {
        "category": "procedural_transform",
        "steps": steps,
        "overall_procedure": "",
        "initial_state": initial,
        "final_state": final,
        "notes": []
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
