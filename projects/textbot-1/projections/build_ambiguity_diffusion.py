#!/usr/bin/env python3
"""
Derive ambiguity diffusion projection from canonical graph.
Each ambiguity node becomes a unit with its possibility field.
Resolved ambiguities become denouement entries.
"""

import json
import sys
from pathlib import Path


def main():
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    units = []
    final_resolution = []

    for amb in graph.get("ambiguities", []):
        unit = {
            "label": amb["label"],
            "applies_to": amb.get("applies_to", []),
            "open_questions": [amb["label"]],
            "possible_interpretations": amb.get("possibilities", []),
            "new_constraints": amb.get("resolved_by", []),
            "collapsed_interpretations": [],
            "status": amb.get("status", "open"),
            "explicit_textual_basis": amb.get("textual_basis", [])
        }

        if amb.get("status") == "resolved":
            unit["collapsed_interpretations"] = amb.get("possibilities", [])[1:]
            final_resolution.append(amb["label"])

        units.append(unit)

    out = {
        "category": "ambiguity_diffusion",
        "units": units,
        "global_denouement": final_resolution,
        "final_open_variables": [
            u["label"] for u in units if u["status"] != "resolved"
        ],
        "notes": []
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
