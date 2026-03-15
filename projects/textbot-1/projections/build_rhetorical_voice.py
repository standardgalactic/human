#!/usr/bin/env python3
"""
Derive rhetorical voice projection from canonical graph.
Claims with stances become rhetorical moves.
"""

import json
import sys
from pathlib import Path


def main():
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    claims = []
    for cl in graph.get("claims", []):
        claims.append({
            "id": cl.get("id", ""),
            "text": cl.get("text", ""),
            "type": cl.get("stance", "assertion"),
            "explicit_textual_basis": cl.get("textual_basis", [])
        })

    argument_structure = []
    for i, cl in enumerate(graph.get("claims", [])):
        role = cl.get("stance", "assertion")
        argument_structure.append({
            "step": cl.get("text", ""),
            "role": role,
            "explicit_textual_basis": cl.get("textual_basis", [])
        })

    out = {
        "category": "rhetorical_voice",
        "claims": claims,
        "tone_shifts": [],
        "emphasis_points": [],
        "contrasts": [],
        "argument_structure": argument_structure,
        "polemical_stance": "",
        "notes": []
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
