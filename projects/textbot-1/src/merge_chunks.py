#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()

    data = []

    for f in sorted(Path(args.input_dir).glob(f"{args.category}_chunk_*.json")):
        data.append(json.loads(f.read_text(encoding="utf-8")))

    merged = {
        "category": args.category,
        "chunks": data
    }

    Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_file).write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Merged {len(data)} chunks -> {args.output_file}")


if __name__ == "__main__":
    main()
