#!/usr/bin/env python3
"""search_corpus.py — query a canonical or corpus graph.

Supports four query modes:
    entity   <name>     find entities matching a name fragment
    claim    <text>     find claims containing a text fragment
    theme    <label>    find themes and their member nodes
    full     <text>     search across all node types

Returns ranked JSON results with provenance, context, and related nodes.

Usage:
    python3 src/search_corpus.py \
        --graph  data/wiki/<stem>/corpus_graph.json \
        --mode   full \
        --query  "constraint propagation"
"""

import argparse
import json
import re
from pathlib import Path


# ── scoring helpers ───────────────────────────────────────────────────────────

def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def score(query_terms: list[str], text: str) -> float:
    """Simple term-frequency score over normalised text."""
    t = normalise(text)
    hits = sum(1 for term in query_terms if term in t)
    return hits / max(1, len(query_terms))


def snippet(text: str, query_terms: list[str], window: int = 120) -> str:
    """Extract a context snippet around the first query term hit."""
    t = normalise(text)
    for term in query_terms:
        idx = t.find(term)
        if idx >= 0:
            start = max(0, idx - 40)
            end   = min(len(text), idx + window)
            return ("…" if start > 0 else "") + text[start:end] + ("…" if end < len(text) else "")
    return text[:window]


# ── node formatters ───────────────────────────────────────────────────────────

def format_entity(node: dict, score_val: float) -> dict:
    return {
        "type":    "entity",
        "id":      node["id"],
        "name":    node["name"],
        "kind":    node.get("type", ""),
        "explicit":   node.get("attributes", {}).get("explicit", []),
        "uncertain":  node.get("attributes", {}).get("uncertain", []),
        "source_docs": node.get("source_docs", []),
        "score":   round(score_val, 3),
    }


def format_event(node: dict, score_val: float) -> dict:
    return {
        "type":    "event",
        "id":      node["id"],
        "label":   node["label"],
        "participants": node.get("participants", []),
        "causes":  node.get("causes", []),
        "effects": node.get("effects", []),
        "basis":   (node.get("textual_basis") or [""])[0][:100],
        "source_docs": node.get("source_docs", []),
        "score":   round(score_val, 3),
    }


def format_claim(node: dict, score_val: float) -> dict:
    return {
        "type":    "claim",
        "id":      node["id"],
        "text":    node["text"],
        "stance":  node.get("stance", ""),
        "supports": node.get("supports", []),
        "opposes":  node.get("opposes", []),
        "basis":   (node.get("textual_basis") or [""])[0][:100],
        "source_docs": node.get("source_docs", []),
        "score":   round(score_val, 3),
    }


def format_theme(node: dict, score_val: float) -> dict:
    return {
        "type":    "theme",
        "id":      node["id"],
        "label":   node["label"],
        "members": node.get("members", []),
        "basis":   (node.get("textual_basis") or [""])[0][:100],
        "source_docs": node.get("source_docs", []),
        "score":   round(score_val, 3),
    }


def format_ambiguity(node: dict, score_val: float) -> dict:
    return {
        "type":          "ambiguity",
        "id":            node["id"],
        "label":         node["label"],
        "possibilities": node.get("possibilities", []),
        "status":        node.get("status", "open"),
        "applies_to":    node.get("applies_to", []),
        "source_docs":   node.get("source_docs", []),
        "score":         round(score_val, 3),
    }


# ── query modes ───────────────────────────────────────────────────────────────

def query_entity(graph: dict, terms: list[str], top_k: int) -> list[dict]:
    results = []
    for node in graph.get("entities", []):
        s = score(terms, node["name"])
        for attr in node.get("attributes", {}).get("explicit", []):
            s = max(s, score(terms, str(attr)) * 0.5)
        if s > 0:
            results.append(format_entity(node, s))
    return sorted(results, key=lambda r: -r["score"])[:top_k]


def query_claim(graph: dict, terms: list[str], top_k: int) -> list[dict]:
    results = []
    for node in graph.get("claims", []):
        s = score(terms, node["text"])
        if s > 0:
            results.append(format_claim(node, s))
    return sorted(results, key=lambda r: -r["score"])[:top_k]


def query_theme(graph: dict, terms: list[str], top_k: int) -> list[dict]:
    results = []
    for node in graph.get("themes", []):
        s = score(terms, node["label"])
        for basis in node.get("textual_basis", []):
            s = max(s, score(terms, basis) * 0.6)
        if s > 0:
            results.append(format_theme(node, s))
    return sorted(results, key=lambda r: -r["score"])[:top_k]


def query_full(graph: dict, terms: list[str], top_k: int) -> list[dict]:
    results = []

    for node in graph.get("entities", []):
        s = score(terms, node["name"])
        if s > 0:
            results.append(format_entity(node, s))

    for node in graph.get("events", []):
        s = score(terms, node["label"])
        for b in node.get("textual_basis", []):
            s = max(s, score(terms, b) * 0.7)
        if s > 0:
            results.append(format_event(node, s))

    for node in graph.get("claims", []):
        s = score(terms, node["text"])
        if s > 0:
            results.append(format_claim(node, s))

    for node in graph.get("themes", []):
        s = score(terms, node["label"])
        if s > 0:
            results.append(format_theme(node, s))

    for node in graph.get("ambiguities", []):
        s = score(terms, node["label"])
        for p in node.get("possibilities", []):
            s = max(s, score(terms, str(p)) * 0.5)
        if s > 0:
            results.append(format_ambiguity(node, s))

    return sorted(results, key=lambda r: -r["score"])[:top_k]


# ── related nodes ─────────────────────────────────────────────────────────────

def find_related(graph: dict, result_ids: set[str], limit: int = 5) -> list[dict]:
    """Return nodes connected to any result node via the relations graph."""
    related_ids: set[str] = set()
    for rel in graph.get("relations", []):
        if rel["source"] in result_ids:
            related_ids.add(rel["target"])
        if rel["target"] in result_ids:
            related_ids.add(rel["source"])
    related_ids -= result_ids

    nodes_by_id = {}
    for key in ("entities", "events", "claims", "themes"):
        for node in graph.get(key, []):
            nodes_by_id[node["id"]] = (key.rstrip("s"), node)

    related = []
    for nid in list(related_ids)[:limit]:
        if nid in nodes_by_id:
            kind, node = nodes_by_id[nid]
            label = node.get("name") or node.get("label") or node.get("text", "")
            related.append({"id": nid, "type": kind, "label": label[:80]})
    return related


# ── main ──────────────────────────────────────────────────────────────────────

MODES = {
    "entity":  query_entity,
    "claim":   query_claim,
    "theme":   query_theme,
    "full":    query_full,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph",  required=True)
    ap.add_argument("--mode",   default="full", choices=list(MODES))
    ap.add_argument("--query",  required=True)
    ap.add_argument("--top",    type=int, default=10)
    ap.add_argument("--json",   action="store_true", help="output raw JSON")
    args = ap.parse_args()

    graph = json.loads(Path(args.graph).read_text(encoding="utf-8"))
    terms = normalise(args.query).split()

    results = MODES[args.mode](graph, terms, args.top)
    result_ids = {r["id"] for r in results}
    related    = find_related(graph, result_ids)

    out = {
        "query":   args.query,
        "mode":    args.mode,
        "terms":   terms,
        "count":   len(results),
        "results": results,
        "related": related,
    }

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    # Human-readable output
    print(f"\n── zebra search ─────────────────────────────")
    print(f"  query : {args.query}")
    print(f"  mode  : {args.mode}  |  {len(results)} results\n")

    for r in results:
        kind  = r["type"].upper()
        label = r.get("name") or r.get("label") or r.get("text", "")[:80]
        score_bar = "█" * int(r["score"] * 10)
        docs  = ", ".join(r.get("source_docs", [])[:2])
        print(f"  [{kind}] {label}")
        print(f"    score {score_bar} {r['score']}  |  docs: {docs or '—'}")
        if r["type"] == "claim":
            print(f"    stance: {r.get('stance','')}")
        if r["type"] == "ambiguity":
            print(f"    status: {r.get('status','')}  |  possibilities: {r.get('possibilities',[])[:3]}")
        print()

    if related:
        print(f"  ── related nodes ──")
        for n in related:
            print(f"    [{n['type']}] {n['label']}")
    print()


if __name__ == "__main__":
    main()
