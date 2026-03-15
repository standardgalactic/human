#!/usr/bin/env python3

import json
import argparse
from pathlib import Path

KEYS = [
    "entities",
    "events",
    "relations",
    "claims",
    "ambiguities",
    "transformations",
    "timeline",
    "themes",
]


def dedupe_objects(items, key_fields):
    seen = {}
    for item in items:
        k = tuple(item.get(f) for f in key_fields)
        if k not in seen:
            seen[k] = item
        else:
            existing = seen[k]
            for field, value in item.items():
                if isinstance(value, list):
                    old = existing.get(field, [])
                    merged = old + [x for x in value if x not in old]
                    existing[field] = merged
                elif field not in existing or existing[field] in ("", None, []):
                    existing[field] = value
    return list(seen.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-file", required=True)
    args = ap.parse_args()

    root = Path(args.input_dir)
    merged = {k: [] for k in KEYS}

    files = sorted(root.glob("canonical_extract_chunk_*.json"))
    if not files:
        files = sorted(root.glob("canonical_extract_*.json"))

    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in KEYS:
            merged[key].extend(data.get(key, []))

    merged["entities"]        = dedupe_objects(merged["entities"],        ["name", "type"])
    merged["events"]          = dedupe_objects(merged["events"],          ["label"])
    merged["relations"]       = dedupe_objects(merged["relations"],       ["source", "relation", "target"])
    merged["claims"]          = dedupe_objects(merged["claims"],          ["text"])
    merged["ambiguities"]     = dedupe_objects(merged["ambiguities"],     ["label"])
    merged["transformations"] = dedupe_objects(merged["transformations"], ["input", "operation", "output"])
    merged["themes"]          = dedupe_objects(merged["themes"],          ["label"])

    timeline = [t for t in merged["timeline"] if isinstance(t, dict) and "event_id" in t]
    timeline.sort(key=lambda x: (x.get("index") is None, x.get("index", 10**9)))
    merged["timeline"] = timeline

    Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_file).write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Canonical graph written: {args.output_file}")


if __name__ == "__main__":
    main()
