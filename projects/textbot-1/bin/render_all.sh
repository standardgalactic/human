#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:?projection directory required}"

python3 render/render_narrative_film.py "$INPUT/narrative_film.json"
python3 render/render_diagrammatic_structure.py "$INPUT/diagrammatic_structure.json"
python3 render/render_ambiguity_diffusion.py "$INPUT/ambiguity_diffusion.json"
python3 render/render_concept_map.py "$INPUT/concept_map.json"
python3 render/render_timeline_causality.py "$INPUT/timeline_causality.json"
python3 render/render_character_state.py "$INPUT/character_state.json"
python3 render/render_sonic_mapping.py "$INPUT/sonic_mapping.json"
python3 render/render_procedural_transform.py "$INPUT/procedural_transform.json"
python3 render/render_rhetorical_voice.py "$INPUT/rhetorical_voice.json"
python3 render/render_structural_summary.py "$INPUT/structural_summary.json"
python3 render/render_constraint_dynamics.py "$INPUT/../canonical/graph.json"
