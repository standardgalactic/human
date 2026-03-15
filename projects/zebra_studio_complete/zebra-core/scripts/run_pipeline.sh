#!/usr/bin/env bash
set -euo pipefail
INPUT="${1:?input file}"
WORK="${2:-work}"
mkdir -p "$WORK/chunks" "$WORK/analyses" "$WORK/graph" "$WORK/projections" "$WORK/tasks"
python src/chunk_text.py "$INPUT" "$WORK/chunks"
# canonical extraction intentionally stubbed here; create a demo graph:
cat > "$WORK/analyses/canonical_extract_chunk_001.json" <<'JSON'
{"entities":[{"id":"ent_001","name":"traveler","type":"person"}],"events":[{"id":"evt_001","label":"traveler enters room","participants":["ent_001"]}],"relations":[],"claims":[],"ambiguities":[{"id":"amb_001","label":"traveler appearance","possibilities":["old","young"],"status":"open"}],"transformations":[],"timeline":[],"themes":[]}
JSON
python src/build_canonical_graph.py --input-dir "$WORK/analyses" --output-file "$WORK/graph/graph.json"
python src/build_projections.py --graph "$WORK/graph/graph.json" --out-dir "$WORK/projections"
python src/generate_scripts.py --projections-dir "$WORK/projections" --out-dir "$WORK/tasks"
echo "Pipeline complete."
