#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:?input text file required}"

CATEGORIES=(
  canonical_extract
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

for CAT in "${CATEGORIES[@]}"; do
  bin/run_one.sh "$CAT" "$INPUT"
done
