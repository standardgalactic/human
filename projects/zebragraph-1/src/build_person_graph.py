#!/usr/bin/env python3
"""build_person_graph.py — build a longitudinal intellectual graph from a personal corpus.

Extends the corpus graph with temporal slicing and person-specific projections:
- intellectual_trajectory: how claims and themes evolve over time
- open_questions:          ambiguities that remain unresolved across the corpus
- concept_network:         the person's unique conceptual vocabulary and connections
- argument_positions:      the stable claims asserted across multiple documents

Usage:
    python3 src/build_person_graph.py \
        --corpus-graph data/wiki/<stem>/corpus_graph.json \
        --manifest     data/wiki/<stem>/manifest.json \
        --output-dir   data/person/<stem>
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path


# ── temporal helpers ──────────────────────────────────────────────────────────

def parse_date(s: str) -> str:
    """Extract YYYY-MM-DD prefix from any ISO date string."""
    if not s:
        return ""
    return s[:10]


def group_by_doc(items: list) -> dict[str, list]:
    """Group nodes by their source document."""
    groups: dict[str, list] = defaultdict(list)
    for item in items:
        for doc in item.get("source_docs", ["__unknown__"]):
            groups[doc].append(item)
    return dict(groups)


# ── projections ───────────────────────────────────────────────────────────────

def intellectual_trajectory(graph: dict, manifest_docs: list) -> dict:
    """Track how claims and themes appear and evolve across documents,
    ordered by document modification date."""

    # Build doc → date index
    doc_dates = {d["slug"]: parse_date(d.get("last_modified_git", "")) for d in manifest_docs}
    doc_paths = {d["slug"]: d["path"] for d in manifest_docs}

    # Sort documents by date
    dated_docs = sorted(
        [(slug, doc_dates.get(slug, ""), doc_paths.get(slug, slug))
         for slug in set(doc_dates)],
        key=lambda x: x[1] or "9999",
    )

    # Assign claims and themes to their first-appearing document
    claim_timeline = []
    seen_claims: set[str] = set()
    for doc_slug, date, path in dated_docs:
        for claim in graph.get("claims", []):
            if doc_slug in claim.get("source_docs", []):
                key = claim["text"][:60]
                if key not in seen_claims:
                    seen_claims.add(key)
                    claim_timeline.append({
                        "date":     date,
                        "document": path,
                        "claim":    claim["text"][:120],
                        "stance":   claim.get("stance", ""),
                        "id":       claim["id"],
                    })

    theme_timeline = []
    seen_themes: set[str] = set()
    for doc_slug, date, path in dated_docs:
        for theme in graph.get("themes", []):
            if doc_slug in theme.get("source_docs", []):
                key = theme["label"]
                if key not in seen_themes:
                    seen_themes.add(key)
                    theme_timeline.append({
                        "date":     date,
                        "document": path,
                        "theme":    theme["label"],
                        "id":       theme["id"],
                    })

    return {
        "projection": "intellectual_trajectory",
        "document_count":  len(dated_docs),
        "claim_timeline":  claim_timeline,
        "theme_timeline":  theme_timeline,
    }


def open_questions(graph: dict) -> dict:
    """All ambiguities that remain unresolved across the entire corpus."""
    unresolved = [
        a for a in graph.get("ambiguities", [])
        if a.get("status", "open") == "open"
    ]
    resolved = [
        a for a in graph.get("ambiguities", [])
        if a.get("status", "open") == "resolved"
    ]

    # Ambiguities that appear across many documents are the most persistent
    persistent = sorted(
        unresolved,
        key=lambda a: len(a.get("source_docs", [])),
        reverse=True,
    )

    return {
        "projection":        "open_questions",
        "total_ambiguities": len(graph.get("ambiguities", [])),
        "unresolved":        len(unresolved),
        "resolved":          len(resolved),
        "persistent_open":   persistent[:20],
        "recently_resolved": sorted(
            resolved,
            key=lambda a: len(a.get("source_docs", [])),
            reverse=True,
        )[:10],
    }


def concept_network(graph: dict) -> dict:
    """The person's unique conceptual vocabulary: entities and themes
    that appear across the most documents, plus the relations between them."""

    # Score entities by document breadth
    entity_scores = [
        {
            "id":      e["id"],
            "name":    e["name"],
            "type":    e.get("type", ""),
            "breadth": len(e.get("source_docs", [])),
            "uncertain": e.get("attributes", {}).get("uncertain", []),
        }
        for e in graph.get("entities", [])
    ]
    entity_scores.sort(key=lambda x: -x["breadth"])

    # Theme network
    theme_scores = [
        {
            "id":      t["id"],
            "label":   t["label"],
            "breadth": len(t.get("source_docs", [])),
            "size":    len(t.get("members", [])),
        }
        for t in graph.get("themes", [])
    ]
    theme_scores.sort(key=lambda x: -x["breadth"])

    # Core relations (between highly-scored nodes)
    top_entity_ids = {e["id"] for e in entity_scores[:30]}
    core_relations = [
        r for r in graph.get("relations", [])
        if r["source"] in top_entity_ids or r["target"] in top_entity_ids
    ]

    return {
        "projection":      "concept_network",
        "core_entities":   entity_scores[:30],
        "core_themes":     theme_scores[:20],
        "core_relations":  core_relations[:50],
    }


def argument_positions(graph: dict) -> dict:
    """The person's stable claimed positions: claims appearing across
    multiple documents with consistent stance."""

    # Group claims by text key
    claim_groups: dict[str, list] = defaultdict(list)
    for c in graph.get("claims", []):
        key = c["text"][:60].lower().strip()
        claim_groups[key].append(c)

    stable = []
    for key, instances in claim_groups.items():
        if len(instances) < 1:
            continue
        breadth = len(set(doc for c in instances for doc in c.get("source_docs", [])))
        stances = [c.get("stance", "") for c in instances]
        dominant_stance = max(set(stances), key=stances.count) if stances else ""
        stable.append({
            "claim":          instances[0]["text"],
            "stance":         dominant_stance,
            "document_count": breadth,
            "instances":      len(instances),
            "ids":            [c["id"] for c in instances],
        })

    stable.sort(key=lambda x: -x["document_count"])

    # Claims that changed stance across documents
    contested = [
        {
            "claim":   instances[0]["text"][:80],
            "stances": list(set(c.get("stance", "") for c in instances)),
        }
        for key, instances in claim_groups.items()
        if len(set(c.get("stance", "") for c in instances)) > 1
    ]

    return {
        "projection":          "argument_positions",
        "total_unique_claims": len(claim_groups),
        "stable_positions":    stable[:30],
        "contested_positions": contested[:10],
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-graph", required=True)
    ap.add_argument("--manifest",     required=True)
    ap.add_argument("--output-dir",   required=True)
    args = ap.parse_args()

    graph    = json.loads(Path(args.corpus_graph).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    docs     = manifest.get("documents", [])

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    projections = {
        "intellectual_trajectory": intellectual_trajectory(graph, docs),
        "open_questions":          open_questions(graph),
        "concept_network":         concept_network(graph),
        "argument_positions":      argument_positions(graph),
    }

    for name, proj in projections.items():
        out_path = out_dir / f"{name}.json"
        out_path.write_text(
            json.dumps(proj, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  {name} → {out_path}")

    # Combined person graph
    combined = {
        "person_graph": True,
        "source_corpus": args.corpus_graph,
        "document_count": len(docs),
        **projections,
    }
    combined_path = out_dir / "person_graph.json"
    combined_path.write_text(
        json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nPerson graph: {combined_path}")


if __name__ == "__main__":
    main()
