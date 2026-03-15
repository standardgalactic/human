#!/usr/bin/env python3
"""build_ambiguity_diffusion.py — project canonical graph into ambiguity-resolution sequence.

This is the projection most directly aligned with the deferred-denouement reading theory:
each ambiguity node is a branch point in interpretation space; resolved_by events are the
constraints that collapse it.

Usage:
    python3 projections/build_ambiguity_diffusion.py data/canonical/essay/graph.json
"""

import json
import sys
from pathlib import Path


def main() -> None:
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    events_by_id = {e["id"]: e for e in graph.get("events", [])}

    units = []
    for amb in graph.get("ambiguities", []):
        resolvers = []
        for rid in amb.get("resolved_by", []):
            if rid in events_by_id:
                resolvers.append(events_by_id[rid]["label"])
            else:
                resolvers.append(rid)

        units.append({
            "id": amb["id"],
            "label": amb["label"],
            "applies_to": amb.get("applies_to", []),
            "open_questions": [amb["label"]],
            "possible_interpretations": amb.get("possibilities", []),
            "n_possibilities": len(amb.get("possibilities", [])),
            "resolving_events": resolvers,
            "collapsed": len(resolvers) > 0 or amb.get("status", "open") == "resolved",
            "textual_basis": amb.get("textual_basis", []),
        })

    # Sort: unresolved first (widest interpretation space), then resolved
    units.sort(key=lambda u: (u["collapsed"], -u["n_possibilities"]))

    resolved = [u["label"] for u in units if u["collapsed"]]
    open_ = [u["label"] for u in units if not u["collapsed"]]

    out = {
        "category": "ambiguity_diffusion",
        "total_ambiguities": len(units),
        "open": len(open_),
        "collapsed": len(resolved),
        "units": units,
        "final_resolution": resolved,
        "remaining_open": open_,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
