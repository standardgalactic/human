#!/usr/bin/env bash
# run_projection.sh — build one projection from canonical graph
set -euo pipefail

PROJECTION="${1:?Usage: bin/run_projection.sh <projection_name> <graph.json>}"
GRAPH="${2:?Usage: bin/run_projection.sh <projection_name> <graph.json>}"

STEM="$(basename "$(dirname "$GRAPH")")"
OUT="data/projections/$STEM/${PROJECTION}.json"

mkdir -p "data/projections/$STEM"

echo "--- projection: $PROJECTION"
python3 "projections/build_${PROJECTION}.py" "$GRAPH" > "$OUT"
python3 src/validate_json.py "$OUT"
echo "Written: $OUT"
