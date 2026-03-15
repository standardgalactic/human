#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-granite4}"
CATEGORY="${1:?category required}"
INPUT="${2:?input text file required}"

BASE="$(basename "$INPUT")"
STEM="${BASE%.*}"

mkdir -p data/chunks/"$STEM"
mkdir -p data/analyses/"$STEM"
mkdir -p data/merged/"$STEM"

python3 src/chunk_text.py "$INPUT" "data/chunks/$STEM"

for CHUNK in data/chunks/"$STEM"/*.txt; do
  NAME="$(basename "$CHUNK" .txt)"

  python3 src/call_ollama.py \
    --model "$MODEL" \
    --prompt-file "prompts/${CATEGORY}.txt" \
    --input-file "$CHUNK" \
    --output-file "data/analyses/$STEM/${CATEGORY}_${NAME}.json"

done

python3 src/merge_chunks.py \
  --category "$CATEGORY" \
  --input-dir "data/analyses/$STEM" \
  --output-file "data/merged/$STEM/${CATEGORY}.json"

python3 src/validate_json.py "data/merged/$STEM/${CATEGORY}.json"

echo "Finished: data/merged/$STEM/${CATEGORY}.json"
