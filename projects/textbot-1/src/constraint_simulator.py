#!/usr/bin/env python3

import json
import sys
from pathlib import Path


def main():
    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    state = {}

    for entity in graph.get("entities", []):
        state[entity["id"]] = {
            "type": "entity",
            "label": entity["name"],
            "activation": 0,
            "certainty": 0.2
        }

    for ambiguity in graph.get("ambiguities", []):
        state[ambiguity["id"]] = {
            "type": "ambiguity",
            "label": ambiguity["label"],
            "possibilities": list(ambiguity.get("possibilities", [])),
            "collapsed": ambiguity.get("status") == "resolved"
        }

    for claim in graph.get("claims", []):
        state[claim["id"]] = {
            "type": "claim",
            "label": claim["text"][:60],
            "activation": 0
        }

    timeline = graph.get("timeline", [])
    history = []

    for step in timeline:
        event_id = step.get("event_id")
        if not event_id:
            continue

        import copy
        history.append({
            "event": event_id,
            "state_snapshot": copy.deepcopy(state)
        })

        for rel in graph.get("relations", []):
            if rel.get("source") == event_id:
                target = rel.get("target")
                if target and target in state:
                    s = state[target]
                    if "activation" in s:
                        s["activation"] += 1
                    if s.get("type") == "ambiguity" and rel.get("relation") == "resolves":
                        s["collapsed"] = True
                        s["possibilities"] = s["possibilities"][:1]

    output = {
        "source_graph": sys.argv[1],
        "steps": len(history),
        "simulation": history
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
