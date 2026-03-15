#!/usr/bin/env python3
"""constraint_simulator.py — simulate constraint propagation over the canonical graph.

Usage:
    python3 src/constraint_simulator.py data/canonical/essay/graph.json \
        > data/projections/essay/constraint_dynamics.json

Models each node as a state vector. Steps through the timeline and propagates
activation, certainty, and ambiguity-collapse along typed edges.
"""

import json
import sys
import copy
from pathlib import Path


def initial_state(graph: dict) -> dict:
    state: dict = {}

    for ent in graph.get("entities", []):
        state[ent["id"]] = {
            "type": "entity",
            "label": ent["name"],
            "activation": 0.0,
            "certainty": 0.2,
            "attributes": ent.get("attributes", {}),
        }

    for evt in graph.get("events", []):
        state[evt["id"]] = {
            "type": "event",
            "label": evt["label"],
            "activation": 0.0,
            "fired": False,
        }

    for clm in graph.get("claims", []):
        state[clm["id"]] = {
            "type": "claim",
            "label": clm["text"][:80],
            "activation": 0.0,
            "stance": clm.get("stance", ""),
        }

    for amb in graph.get("ambiguities", []):
        state[amb["id"]] = {
            "type": "ambiguity",
            "label": amb["label"],
            "possibilities": list(amb.get("possibilities", [])),
            "collapsed": amb.get("status", "open") == "resolved",
        }

    for thm in graph.get("themes", []):
        state[thm["id"]] = {
            "type": "theme",
            "label": thm["label"],
            "activation": 0.0,
        }

    for trn in graph.get("transformations", []):
        state[trn["id"]] = {
            "type": "transformation",
            "label": f"{trn.get('input','')} → {trn.get('output','')}",
            "fired": False,
        }

    return state


def propagate(state: dict, edges: list[dict], fired_id: str) -> dict:
    """Propagate effects of a newly activated node along typed edges."""
    new_state = copy.deepcopy(state)

    for edge in edges:
        if edge["source"] != fired_id:
            continue
        target = edge["target"]
        rel = edge.get("type", edge.get("relation", ""))

        if target not in new_state:
            continue

        node = new_state[target]

        if rel == "participates_in":
            node["activation"] = node.get("activation", 0.0) + 0.5
            node["certainty"] = min(1.0, node.get("certainty", 0.2) + 0.1)

        elif rel == "causes":
            node["activation"] = node.get("activation", 0.0) + 0.8

        elif rel == "resolves":
            # Collapse the ambiguity
            if node.get("type") == "ambiguity" and not node.get("collapsed"):
                poss = node.get("possibilities", [])
                node["possibilities"] = poss[:1]  # keep most probable
                node["collapsed"] = True

        elif rel == "supports":
            node["activation"] = node.get("activation", 0.0) + 0.4

        elif rel == "belongs_to":
            node["activation"] = node.get("activation", 0.0) + 0.3

        elif rel == "transforms":
            node["fired"] = True

    return new_state


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: constraint_simulator.py <canonical_graph.json>", file=sys.stderr)
        sys.exit(1)

    graph = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    # Normalise edge schema: accept both "relation" and "type" as the edge label
    edges = graph.get("relations", [])
    for e in edges:
        if "type" not in e and "relation" in e:
            e["type"] = e["relation"]

    state = initial_state(graph)
    history: list[dict] = []

    # Record initial state
    history.append({
        "step": 0,
        "event": "__initial__",
        "state": copy.deepcopy(state),
    })

    timeline = graph.get("timeline", [])
    if not timeline:
        # Fall back to event order if timeline is absent
        timeline = [
            {"index": i + 1, "event_id": evt["id"]}
            for i, evt in enumerate(graph.get("events", []))
        ]

    for step_data in timeline:
        event_id = step_data.get("event_id", "")
        if not event_id or event_id not in state:
            continue

        # Fire the event
        state[event_id]["activation"] = 1.0
        state[event_id]["fired"] = True

        state = propagate(state, edges, event_id)

        history.append({
            "step": step_data.get("index", len(history)),
            "event": state[event_id].get("label", event_id),
            "event_id": event_id,
            "state": copy.deepcopy(state),
        })

    # Summary statistics per step
    summary = []
    for h in history:
        s = h["state"]
        ambiguities_open = sum(
            1 for n in s.values() if n.get("type") == "ambiguity" and not n.get("collapsed")
        )
        ambiguities_collapsed = sum(
            1 for n in s.values() if n.get("type") == "ambiguity" and n.get("collapsed")
        )
        avg_activation = 0.0
        activated = [n.get("activation", 0.0) for n in s.values() if "activation" in n]
        if activated:
            avg_activation = round(sum(activated) / len(activated), 3)

        summary.append({
            "step": h["step"],
            "event": h["event"],
            "ambiguities_open": ambiguities_open,
            "ambiguities_collapsed": ambiguities_collapsed,
            "avg_activation": avg_activation,
        })

    out = {
        "category": "constraint_dynamics",
        "total_steps": len(history),
        "summary": summary,
        "simulation": history,
    }

    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
