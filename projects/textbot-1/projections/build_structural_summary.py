#!/usr/bin/env python3
"""
Derive structural summary projection from canonical graph.
Extracts premises, definitions, contradictions, resolutions, open variables.
"""

import json
import sys
from pathlib import Path


def main():
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    # Claims with stance 'asserted' or 'assumed' become premises
    premises = []
    for cl in graph.get("claims", []):
        if cl.get("stance") in ("asserted", "assumed", ""):
            premises.append({
                "id": cl.get("id", ""),
                "text": cl.get("text", ""),
                "explicit_textual_basis": cl.get("textual_basis", [])
            })

    # Definitions from entities with explicit attributes
    definitions = []
    for ent in graph.get("entities", []):
        attrs = ent.get("attributes", {}).get("explicit", [])
        if attrs:
            definitions.append({
                "term": ent["name"],
                "definition": "; ".join(attrs),
                "explicit_textual_basis": ent.get("textual_basis", [])
            })

    # Open variables from unresolved ambiguities
    open_variables = []
    for amb in graph.get("ambiguities", []):
        if amb.get("status") != "resolved":
            open_variables.append({
                "label": amb["label"],
                "description": f"Possible values: {', '.join(amb.get('possibilities', []))}",
                "explicit_textual_basis": amb.get("textual_basis", [])
            })

    out = {
        "category": "structural_summary",
        "premises": premises,
        "definitions": definitions,
        "contradictions": [],
        "resolutions": [],
        "open_variables": open_variables,
        "central_argument": "",
        "notes": []
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
