#!/usr/bin/env bash
# run_canonical.sh — chunk text, call Ollama, merge into canonical graph
set -euo pipefail

MODEL="${MODEL:-granite4}"
INPUT="${1:?Usage: bin/run_canonical.sh <input_text_file>}"

BASE="$(basename "$INPUT")"
STEM="${BASE%.*}"

echo "--- chunking: $INPUT"
mkdir -p "data/chunks/$STEM"
python3 src/chunk_text.py "$INPUT" "data/chunks/$STEM"

echo "--- canonical extraction (model=$MODEL)"
mkdir -p "data/analyses/$STEM"

for CHUNK in "data/chunks/$STEM"/*.txt; do
  NAME="$(basename "$CHUNK" .txt)"
  OUT="data/analyses/$STEM/canonical_extract_${NAME}.json"
  if [[ -f "$OUT" ]]; then
    echo "    skip (cached): $OUT"
    continue
  fi
  echo "    analyzing: $CHUNK"
  python3 src/call_ollama.py \
    --model "$MODEL" \
    --prompt-file prompts/canonical_extract.txt \
    --input-file "$CHUNK" \
    --output-file "$OUT"
done

echo "--- merging canonical graph"
mkdir -p "data/canonical/$STEM"
python3 src/build_canonical_graph.py \
  --input-dir "data/analyses/$STEM" \
  --output-file "data/canonical/$STEM/graph.json"

python3 src/validate_json.py "data/canonical/$STEM/graph.json"
echo "Canonical graph: data/canonical/$STEM/graph.json"
