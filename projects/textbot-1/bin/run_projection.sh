#!/usr/bin/env bash
set -euo pipefail

PROJECTION="${1:?projection required}"
GRAPH="${2:?canonical graph required}"
OUT="${3:?output file required}"

python3 "projections/build_${PROJECTION}.py" "$GRAPH" > "$OUT"
python3 src/validate_json.py "$OUT"
