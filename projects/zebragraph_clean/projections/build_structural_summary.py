#!/usr/bin/env python3
"""build_structural_summary.py — project canonical graph into minimal logical skeleton.

Premises, definitions, contradictions, resolutions, and open variables —
the bare bones of the text's argumentative structure.

Usage:
    python3 projections/build_structural_summary.py data/canonical/essay/graph.json
"""

import json
import sys
from pathlib import Path


def main() -> None:
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    claims = graph.get("claims", [])
    relations = graph.get("relations", [])
    ambiguities = graph.get("ambiguities", [])
    transformations = graph.get("transformations", [])
    entities = graph.get("entities", [])

    # Classify claims by stance
    premises    = [c for c in claims if c.get("stance") in ("asserted", "premise", "given", "")]
    definitions = [c for c in claims if c.get("stance") in ("definition", "defines")]
    contested   = [c for c in claims if c.get("stance") in ("contested", "questioned", "disputed")]

    # Contradictions: claims linked by opposes
    opposes_edges = [
        r for r in relations
        if r.get("relation", r.get("type", "")) == "opposes"
    ]
    claim_ids = {c["id"] for c in claims}
    contradictions = [
        {
            "claim_a": r["source"],
            "claim_b": r["target"],
        }
        for r in opposes_edges
        if r["source"] in claim_ids and r["target"] in claim_ids
    ]

    # Resolutions: ambiguities with resolved_by events
    resolutions = [
        {
            "ambiguity": a["label"],
            "resolved_by": a.get("resolved_by", []),
        }
        for a in ambiguities
        if a.get("resolved_by") and a.get("status", "open") == "resolved"
    ]

    # Open variables: unresolved ambiguities + entities with uncertain attributes
    open_variables = [a["label"] for a in ambiguities if a.get("status", "open") != "resolved"]
    for ent in entities:
        for attr in ent.get("attributes", {}).get("uncertain", []):
            label = f"{ent['name']}.{attr}"
            if label not in open_variables:
                open_variables.append(label)

    out = {
        "category": "structural_summary",
        "premises": [c["text"] for c in premises],
        "definitions": [c["text"] for c in definitions],
        "contested_claims": [c["text"] for c in contested],
        "contradictions": contradictions,
        "resolutions": resolutions,
        "open_variables": open_variables,
        "transformation_count": len(transformations),
        "total_claims": len(claims),
        "total_entities": len(entities),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
