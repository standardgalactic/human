#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-granite4}"
INPUT="${1:?input text file required}"

BASE="$(basename "$INPUT")"
STEM="${BASE%.*}"

mkdir -p data/chunks/"$STEM" data/analyses/"$STEM" data/canonical/"$STEM"

python3 src/chunk_text.py "$INPUT" "data/chunks/$STEM"

for CHUNK in data/chunks/"$STEM"/*.txt; do
  NAME="$(basename "$CHUNK" .txt)"
  python3 src/call_ollama.py \
    --model "$MODEL" \
    --prompt-file "prompts/canonical_extract.txt" \
    --input-file "$CHUNK" \
    --output-file "data/analyses/$STEM/canonical_extract_${NAME}.json"
done

python3 src/build_canonical_graph.py \
  --input-dir "data/analyses/$STEM" \
  --output-file "data/canonical/$STEM/graph.json"

python3 src/validate_json.py "data/canonical/$STEM/graph.json"
echo "Built canonical graph: data/canonical/$STEM/graph.json"
