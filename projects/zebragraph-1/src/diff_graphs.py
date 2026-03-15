#!/usr/bin/env python3
"""diff_graphs.py — compare two canonical or corpus graphs.

Computes a structural diff: new nodes, removed nodes, modified nodes,
new relations, and evolution of ambiguity status.

Useful for tracking how a body of work (or a person's writing) evolves
over time when graphs are built from different versions or time slices
of a corpus.

Usage:
    python3 src/diff_graphs.py \
        --before data/canonical/essay_v1/graph.json \
        --after  data/canonical/essay_v2/graph.json \
        --output data/diffs/essay_v1_v2.json
"""

import argparse
import json
from pathlib import Path


# ── key functions (must match build_canonical_graph.py) ─────────────────────

DEDUP_FIELDS = {
    "entities":        ["name", "type"],
    "events":          ["label"],
    "relations":       ["source", "relation", "target"],
    "claims":          ["text"],
    "ambiguities":     ["label"],
    "transformations": ["input", "operation", "output"],
    "themes":          ["label"],
}


def stable_key(item: dict, fields: list) -> str:
    return "||".join(str(item.get(f, "")).strip().lower() for f in fields)


def index_by_key(items: list, fields: list) -> dict[str, dict]:
    return {stable_key(item, fields): item for item in items}


# ── diff primitives ───────────────────────────────────────────────────────────

def diff_node_list(before: list, after: list, fields: list, node_type: str) -> dict:
    b = index_by_key(before, fields)
    a = index_by_key(after,  fields)

    added   = [a[k] for k in a if k not in b]
    removed = [b[k] for k in b if k not in a]

    modified = []
    for k in b:
        if k not in a:
            continue
        bnode, anode = b[k], a[k]
        changes = {}
        all_fields = set(bnode) | set(anode)
        for f in all_fields:
            bv, av = bnode.get(f), anode.get(f)
            if bv != av:
                changes[f] = {"before": bv, "after": av}
        if changes:
            modified.append({
                "key":     k,
                "node":    anode,
                "changes": changes,
            })

    return {
        "type":     node_type,
        "added":    added,
        "removed":  removed,
        "modified": modified,
        "count_before": len(before),
        "count_after":  len(after),
        "delta":    len(after) - len(before),
    }


def diff_ambiguities(before: list, after: list) -> dict:
    """Special diff for ambiguities: track resolution status changes."""
    base = diff_node_list(before, after, DEDUP_FIELDS["ambiguities"], "ambiguities")

    b_idx = index_by_key(before, DEDUP_FIELDS["ambiguities"])
    a_idx = index_by_key(after,  DEDUP_FIELDS["ambiguities"])

    newly_resolved = []
    newly_opened   = []
    for k in b_idx:
        if k not in a_idx:
            continue
        bs = b_idx[k].get("status", "open")
        as_ = a_idx[k].get("status", "open")
        if bs == "open" and as_ == "resolved":
            newly_resolved.append(a_idx[k]["label"])
        elif bs == "resolved" and as_ == "open":
            newly_opened.append(a_idx[k]["label"])

    base["newly_resolved"] = newly_resolved
    base["newly_opened"]   = newly_opened
    return base


def diff_claims(before: list, after: list) -> dict:
    """Special diff for claims: track stance changes."""
    base = diff_node_list(before, after, DEDUP_FIELDS["claims"], "claims")

    b_idx = index_by_key(before, DEDUP_FIELDS["claims"])
    a_idx = index_by_key(after,  DEDUP_FIELDS["claims"])

    stance_changes = []
    for k in b_idx:
        if k not in a_idx:
            continue
        bs = b_idx[k].get("stance", "")
        as_ = a_idx[k].get("stance", "")
        if bs != as_:
            stance_changes.append({
                "claim":  a_idx[k]["text"][:60],
                "before": bs,
                "after":  as_,
            })
    base["stance_changes"] = stance_changes
    return base


# ── summary statistics ────────────────────────────────────────────────────────

def summary(diffs: dict) -> dict:
    total_added   = sum(len(d["added"])   for d in diffs.values() if isinstance(d, dict) and "added" in d)
    total_removed = sum(len(d["removed"]) for d in diffs.values() if isinstance(d, dict) and "removed" in d)
    total_modified= sum(len(d["modified"])for d in diffs.values() if isinstance(d, dict) and "modified" in d)

    amb = diffs.get("ambiguities", {})
    clm = diffs.get("claims", {})

    return {
        "total_added":          total_added,
        "total_removed":        total_removed,
        "total_modified":       total_modified,
        "ambiguities_resolved": len(amb.get("newly_resolved", [])),
        "ambiguities_opened":   len(amb.get("newly_opened",   [])),
        "stance_changes":       len(clm.get("stance_changes",  [])),
        "net_growth": {
            k: diffs[k]["delta"]
            for k in diffs if isinstance(diffs[k], dict) and "delta" in diffs[k]
        },
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before",  required=True)
    ap.add_argument("--after",   required=True)
    ap.add_argument("--output",  default=None)
    ap.add_argument("--human",   action="store_true", help="print human-readable summary")
    args = ap.parse_args()

    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after  = json.loads(Path(args.after).read_text(encoding="utf-8"))

    diffs = {
        "entities":        diff_node_list(
            before.get("entities", []), after.get("entities", []),
            DEDUP_FIELDS["entities"], "entities"),
        "events":          diff_node_list(
            before.get("events", []), after.get("events", []),
            DEDUP_FIELDS["events"], "events"),
        "claims":          diff_claims(
            before.get("claims", []), after.get("claims", [])),
        "ambiguities":     diff_ambiguities(
            before.get("ambiguities", []), after.get("ambiguities", [])),
        "themes":          diff_node_list(
            before.get("themes", []), after.get("themes", []),
            DEDUP_FIELDS["themes"], "themes"),
        "transformations": diff_node_list(
            before.get("transformations", []), after.get("transformations", []),
            DEDUP_FIELDS["transformations"], "transformations"),
        "relations":       diff_node_list(
            before.get("relations", []), after.get("relations", []),
            DEDUP_FIELDS["relations"], "relations"),
    }

    result = {
        "before": args.before,
        "after":  args.after,
        "summary": summary(diffs),
        "diffs":   diffs,
    }

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Diff written: {args.output}")

    if args.human or not args.output:
        s = result["summary"]
        print(f"\n── zebra diff ───────────────────────────────")
        print(f"  before : {args.before}")
        print(f"  after  : {args.after}\n")
        print(f"  added    {s['total_added']}")
        print(f"  removed  {s['total_removed']}")
        print(f"  modified {s['total_modified']}")
        print(f"\n  ambiguities resolved : {s['ambiguities_resolved']}")
        print(f"  ambiguities opened   : {s['ambiguities_opened']}")
        print(f"  stance changes       : {s['stance_changes']}")
        print(f"\n  net growth by type:")
        for k, v in s["net_growth"].items():
            sign = "+" if v >= 0 else ""
            print(f"    {k:<20} {sign}{v}")

        amb = diffs["ambiguities"]
        if amb.get("newly_resolved"):
            print(f"\n  newly resolved ambiguities:")
            for label in amb["newly_resolved"]:
                print(f"    ✓  {label}")
        if amb.get("newly_opened"):
            print(f"\n  newly opened ambiguities:")
            for label in amb["newly_opened"]:
                print(f"    ?  {label}")

        clm = diffs["claims"]
        if clm.get("stance_changes"):
            print(f"\n  stance changes:")
            for sc in clm["stance_changes"]:
                print(f"    {sc['claim']}  [{sc['before']} → {sc['after']}]")
        print()


if __name__ == "__main__":
    main()
