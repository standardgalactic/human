#!/usr/bin/env python3
"""validate_json.py — verify a file contains valid JSON and report basic stats.

Usage:
    python3 src/validate_json.py <file.json>

Exits with code 1 if the file is invalid or missing.
"""

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: validate_json.py <file.json>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"INVALID JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)

    size = path.stat().st_size
    keys = list(data.keys()) if isinstance(data, dict) else f"[list, len={len(data)}]"
    print(f"OK  {path}  ({size} bytes)  keys={keys}")


if __name__ == "__main__":
    main()
