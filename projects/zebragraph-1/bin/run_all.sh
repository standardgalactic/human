#!/usr/bin/env bash
# run_all.sh — full pipeline: canonical extraction + all projections
set -euo pipefail

INPUT="${1:?Usage: bin/run_all.sh <input_text_file>}"

echo "=== textbot: full pipeline ==="
echo "Input: $INPUT"

# 1. Canonical extraction
bin/run_canonical.sh "$INPUT"

BASE="$(basename "$INPUT")"
STEM="${BASE%.*}"
GRAPH="data/canonical/$STEM/graph.json"

# 2. All projections
PROJECTIONS=(
  narrative_film
  diagrammatic_structure
  ambiguity_diffusion
  rhetorical_voice
  concept_map
  procedural_transform
  timeline_causality
  character_state
  sonic_mapping
  structural_summary
)

mkdir -p "data/projections/$STEM"

for P in "${PROJECTIONS[@]}"; do
  echo "--- projection: $P"
  python3 "projections/build_${P}.py" "$GRAPH" \
    > "data/projections/$STEM/${P}.json"
  python3 src/validate_json.py "data/projections/$STEM/${P}.json"
done

echo ""
echo "=== done ==="
echo "Canonical graph : data/canonical/$STEM/graph.json"
echo "Projections     : data/projections/$STEM/"
