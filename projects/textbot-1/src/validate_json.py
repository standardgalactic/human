#!/usr/bin/env python3

import json
import sys
from pathlib import Path

file = Path(sys.argv[1])

try:
    data = json.loads(file.read_text(encoding="utf-8"))
    print(f"JSON valid: {file}")
    sys.exit(0)
except Exception as e:
    print(f"Invalid JSON in {file}: {e}", file=sys.stderr)
    sys.exit(1)
