#!/usr/bin/env bash
# render_all.sh — render all projection JSONs into videos/images
set -euo pipefail

STEM="${1:?Usage: bin/render_all.sh <stem>}"

PROJ_DIR="data/projections/$STEM"
GRAPH="data/canonical/$STEM/graph.json"

echo "=== textbot: render all ==="

RENDERERS=(
  diagrammatic_structure
  ambiguity_diffusion
  concept_diffusion
  constraint_dynamics
  timeline_causality
  character_state
  sonic_mapping
  narrative_film
  structural_summary
)

mkdir -p data/videos data/frames

for R in "${RENDERERS[@]}"; do
  PROJ="$PROJ_DIR/${R}.json"
  # concept_diffusion and constraint_dynamics take the canonical graph directly
  if [[ "$R" == "constraint_dynamics" ]]; then
    echo "--- render: $R"
    python3 "render/render_${R}.py" "$GRAPH"
  elif [[ -f "$PROJ" ]]; then
    echo "--- render: $R"
    python3 "render/render_${R}.py" "$PROJ"
  else
    echo "    skip (no projection): $R"
  fi
done

echo ""
echo "=== done: data/videos/ ==="
