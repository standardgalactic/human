#!/usr/bin/env python3
"""build_rhetorical_voice.py — project canonical graph into argument / rhetorical structure.

Usage:
    python3 projections/build_rhetorical_voice.py data/canonical/essay/graph.json
"""

import json
import sys
from pathlib import Path


def main() -> None:
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    claims = graph.get("claims", [])
    relations = graph.get("relations", [])

    # Classify relations involving claims
    support_edges = [r for r in relations if r.get("relation", r.get("type", "")) == "supports"]
    oppose_edges  = [r for r in relations if r.get("relation", r.get("type", "")) == "opposes"]

    claim_records = []
    for c in claims:
        supports = [r["target"] for r in support_edges if r["source"] == c["id"]]
        opposes  = [r["target"] for r in oppose_edges  if r["source"] == c["id"]]
        claim_records.append({
            "id": c["id"],
            "text": c["text"],
            "stance": c.get("stance", ""),
            "supports": supports,
            "opposes": opposes,
            "textual_basis": c.get("textual_basis", []),
        })

    # Tone distribution from stances
    stances = [c.get("stance", "") for c in claims]
    tone_counts: dict[str, int] = {}
    for s in stances:
        if s:
            tone_counts[s] = tone_counts.get(s, 0) + 1

    out = {
        "category": "rhetorical_voice",
        "total_claims": len(claims),
        "tone_distribution": tone_counts,
        "argument_structure": claim_records,
        "emphasis_points": [
            c["text"][:80] for c in claims if c.get("stance") in ("asserted", "emphasized")
        ],
        "contrasts": [
            {"claim": r["source"], "opposes": r["target"]} for r in oppose_edges
        ],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
