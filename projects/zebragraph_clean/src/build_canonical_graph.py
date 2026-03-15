#!/usr/bin/env python3
"""build_canonical_graph.py — merge per-chunk canonical JSON into one graph.

Usage:
    python3 src/build_canonical_graph.py \
        --input-dir data/analyses/essay \
        --output-file data/canonical/essay/graph.json

Deduplication is performed on each node type using a stable key derived
from the most semantically identifying fields. Lists are union-merged so
that textual_basis evidence accumulates across chunks.
"""

import argparse
import json
from pathlib import Path

# Fields used as deduplication keys per node type
DEDUP_KEYS: dict[str, list[str]] = {
    "entities": ["name", "type"],
    "events": ["label"],
    "relations": ["source", "relation", "target"],
    "claims": ["text"],
    "ambiguities": ["label"],
    "transformations": ["input", "operation", "output"],
    "themes": ["label"],
}

TOP_LEVEL_KEYS = list(DEDUP_KEYS.keys()) + ["timeline"]


def stable_key(item: dict, fields: list[str]) -> tuple:
    return tuple(str(item.get(f, "")).strip().lower() for f in fields)


def dedupe(items: list[dict], key_fields: list[str]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for item in items:
        k = stable_key(item, key_fields)
        if k not in seen:
            seen[k] = dict(item)
        else:
            existing = seen[k]
            # Merge list fields (union, preserve order)
            for field, value in item.items():
                if isinstance(value, list):
                    old: list = existing.get(field, [])
                    existing[field] = old + [x for x in value if x not in old]
                elif field not in existing or existing[field] in ("", None, []):
                    existing[field] = value
    return list(seen.values())


def sort_timeline(timeline: list[dict]) -> list[dict]:
    valid = [t for t in timeline if isinstance(t, dict) and "event_id" in t]
    return sorted(valid, key=lambda x: (x.get("index") is None, x.get("index", 10**9)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-file", required=True)
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    merged: dict[str, list] = {k: [] for k in TOP_LEVEL_KEYS}

    chunk_files = sorted(input_dir.glob("canonical_extract_chunk_*.json"))
    if not chunk_files:
        # Also accept any canonical_extract_*.json pattern
        chunk_files = sorted(input_dir.glob("canonical_extract_*.json"))

    if not chunk_files:
        print(f"WARNING: No canonical chunk files found in {input_dir}")

    for path in chunk_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"WARNING: Skipping malformed JSON in {path}: {e}")
            continue
        for key in TOP_LEVEL_KEYS:
            items = data.get(key, [])
            if isinstance(items, list):
                merged[key].extend(items)

    # Deduplicate all typed node lists
    for key, key_fields in DEDUP_KEYS.items():
        merged[key] = dedupe(merged[key], key_fields)

    # Sort timeline
    merged["timeline"] = sort_timeline(merged["timeline"])

    out_path = Path(args.output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

    counts = {k: len(merged[k]) for k in TOP_LEVEL_KEYS}
    print("Canonical graph written:", out_path)
    print("Node counts:", counts)


if __name__ == "__main__":
    main()
