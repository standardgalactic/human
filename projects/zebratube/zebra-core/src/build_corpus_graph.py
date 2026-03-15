#!/usr/bin/env python3
"""build_corpus_graph.py — merge all per-document canonical graphs into one corpus graph.

The corpus graph is structurally identical to a single-document canonical
graph but carries additional provenance fields recording which document each
node originated from.

Usage:
    python3 src/build_corpus_graph.py \
        --analyses-dir data/wiki/<stem>/analyses \
        --manifest     data/wiki/<stem>/manifest.json \
        --output-file  data/wiki/<stem>/corpus_graph.json
"""

import argparse
import json
from pathlib import Path

TYPED_KEYS = [
    "entities", "events", "relations", "claims",
    "ambiguities", "transformations", "themes",
]
ALL_KEYS = TYPED_KEYS + ["timeline"]

DEDUP_FIELDS = {
    "entities":        ["name", "type"],
    "events":          ["label"],
    "relations":       ["source", "relation", "target"],
    "claims":          ["text"],
    "ambiguities":     ["label"],
    "transformations": ["input", "operation", "output"],
    "themes":          ["label"],
}


def stable_key(item: dict, fields: list) -> tuple:
    return tuple(str(item.get(f, "")).strip().lower() for f in fields)


def dedupe(items: list, fields: list) -> list:
    seen: dict[tuple, dict] = {}
    for item in items:
        k = stable_key(item, fields)
        if k not in seen:
            seen[k] = dict(item)
        else:
            existing = seen[k]
            for field, value in item.items():
                if isinstance(value, list):
                    old = existing.get(field, [])
                    existing[field] = old + [x for x in value if x not in old]
                elif field not in existing or existing[field] in ("", None, []):
                    existing[field] = value
    return list(seen.values())


def stamp_provenance(items: list, doc_slug: str) -> list:
    """Add source_doc field to every node for cross-document linking."""
    result = []
    for item in items:
        node = dict(item)
        sources = node.get("source_docs", [])
        if doc_slug not in sources:
            sources = sources + [doc_slug]
        node["source_docs"] = sources
        result.append(node)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyses-dir", required=True)
    ap.add_argument("--manifest",     required=True)
    ap.add_argument("--output-file",  required=True)
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    doc_slugs = {d["slug"] for d in manifest["documents"]}

    corpus: dict[str, list] = {k: [] for k in ALL_KEYS}
    analyses_dir = Path(args.analyses_dir)

    loaded = 0
    for path in sorted(analyses_dir.glob("canonical_extract_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        # Derive the document slug from the filename
        # filename pattern: canonical_extract_<doc_slug>_chunk_NNN.json
        name = path.stem  # canonical_extract_<slug>_chunk_NNN
        parts = name.split("_chunk_")
        doc_slug = parts[0].replace("canonical_extract_", "", 1) if len(parts) > 1 else name

        for key in TYPED_KEYS:
            items = data.get(key, [])
            stamped = stamp_provenance(items, doc_slug)
            corpus[key].extend(stamped)

        corpus["timeline"].extend(data.get("timeline", []))
        loaded += 1

    # Deduplicate
    for key in TYPED_KEYS:
        corpus[key] = dedupe(corpus[key], DEDUP_FIELDS[key])

    # Sort timeline
    tl = [t for t in corpus["timeline"] if isinstance(t, dict) and "event_id" in t]
    tl.sort(key=lambda x: (x.get("index") is None, x.get("index", 10**9)))
    corpus["timeline"] = tl

    # Summary statistics
    stats = {k: len(corpus[k]) for k in ALL_KEYS}
    stats["source_documents"] = loaded

    out = {
        "corpus_graph": True,
        "repo": manifest.get("repo", ""),
        "stats": stats,
        **corpus,
    }

    Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_file).write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Corpus graph: {args.output_file}")
    print(f"Stats: {stats}")


if __name__ == "__main__":
    main()
