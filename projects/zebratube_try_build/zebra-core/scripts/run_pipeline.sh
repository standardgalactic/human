#!/usr/bin/env bash
set -euo pipefail
INPUT="${1:?input file}"
WORK="${2:-work}"
mkdir -p "$WORK/chunks" "$WORK/analyses" "$WORK/graph" "$WORK/projections" "$WORK/tasks"
python -m src.chunk_text "$INPUT" "$WORK/chunks"
for c in "$WORK"/chunks/*.txt; do
  b="$(basename "$c" .txt)"
  python -m src.call_ollama --model granite4 --prompt-file prompts/canonical_extract.txt --input-file "$c" --output-file "$WORK/analyses/canonical_extract_${b}.json"
done
python -m src.build_canonical_graph --input-dir "$WORK/analyses" --output-file "$WORK/graph/graph.json"
python -m src.build_projections --graph "$WORK/graph/graph.json" --out-dir "$WORK/projections"
python -m src.generate_scripts --projections-dir "$WORK/projections" --out-dir "$WORK/tasks"
