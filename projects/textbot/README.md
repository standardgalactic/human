# textbot — text physics engine

A modular pipeline that reads a text, builds one canonical semantic graph,
and projects it into ten distinct interpretive outputs: film storyboard,
constraint diagram, ambiguity diffusion animation, concept field,
timeline, character states, sonic arc, procedural steps, rhetorical
structure, and logical skeleton.

The key architectural principle is that the LLM is called only once
(canonical extraction). Everything downstream is deterministic Python.

---

## Prerequisites

```
# Python dependencies
pip install requests matplotlib networkx

# Optional — needed for real semantic embeddings in concept_diffusion
pip install sentence-transformers scikit-learn

# Optional — MIDI export
pip install pretty_midi

# ffmpeg — needed to compile frame sequences into MP4
# macOS:  brew install ffmpeg
# Debian: apt-get install ffmpeg

# Ollama — local LLM server
# https://ollama.com
ollama pull granite4       # or whichever model you prefer
ollama serve               # must be running before you use textbot
```

---

## Quick start

```bash
# Place your text in data/input/
cp my_essay.txt data/input/

# Full pipeline: extract + project
bin/run_all.sh data/input/my_essay.txt

# Then render all visualisations
bin/render_all.sh my_essay
```

Outputs land in:

```
data/canonical/my_essay/graph.json      ← the semantic graph
data/projections/my_essay/*.json        ← ten projection files
data/videos/                            ← PNG and MP4 outputs
```

---

## Architecture

```
text
 └─► chunk_text.py          paragraph-preserving chunks
      └─► call_ollama.py     single LLM call per chunk (temperature=0)
           └─► build_canonical_graph.py   merge + deduplicate
                └─► canonical graph (graph.json)
                     ├─► build_narrative_film.py
                     ├─► build_diagrammatic_structure.py
                     ├─► build_ambiguity_diffusion.py    ← deferred denouement
                     ├─► build_rhetorical_voice.py
                     ├─► build_concept_map.py
                     ├─► build_procedural_transform.py
                     ├─► build_timeline_causality.py
                     ├─► build_character_state.py
                     ├─► build_sonic_mapping.py
                     └─► build_structural_summary.py
                          └─► render_*.py → PNG / MP4
```

The canonical graph schema has eight node types:
`entities`, `events`, `relations`, `claims`,
`ambiguities`, `transformations`, `timeline`, `themes`.

Each relation carries a typed label:
`participates_in`, `causes`, `resolves`, `supports`,
`opposes`, `belongs_to`, `transforms`.

---

## Projection summary

| Projection | What it shows |
|---|---|
| `narrative_film` | Scene list with characters, locations, uncertain details |
| `diagrammatic_structure` | Typed node/edge graph of the text's constraint network |
| `ambiguity_diffusion` | Interpretation space narrowing to denouement |
| `rhetorical_voice` | Claim structure, stances, supports, oppositions |
| `concept_map` | Thematic clusters and cross-cluster connections |
| `procedural_transform` | Text as ordered operations / state machine |
| `timeline_causality` | Events ordered by causality and time |
| `character_state` | Entity state vectors evolving under narrative constraints |
| `sonic_mapping` | Tempo, tension, harmonic arc across narrative time |
| `structural_summary` | Premises, definitions, contradictions, open variables |

---

## Running individual steps

```bash
# Canonical extraction only
bin/run_canonical.sh data/input/essay.txt

# Single projection
bin/run_projection.sh ambiguity_diffusion data/canonical/essay/graph.json

# Single render
python3 render/render_ambiguity_diffusion.py data/projections/essay/ambiguity_diffusion.json

# Constraint dynamics (reads canonical graph directly)
python3 src/constraint_simulator.py data/canonical/essay/graph.json \
  > data/projections/essay/constraint_dynamics.json
python3 render/render_constraint_dynamics.py data/canonical/essay/graph.json
```

---

## Changing the model

```bash
MODEL=llama3.2 bin/run_all.sh data/input/essay.txt
```

Any model available in your local Ollama instance works.
`granite4` is the default because IBM recommends temperature=0
for structured inference tasks, which aligns with this pipeline's needs.

---

## Design notes

**Why one LLM call?**
Concentrating uncertainty in a single extraction step makes the rest of the
system transparent and debuggable. If a projection looks wrong, the place to
look is `data/analyses/<stem>/canonical_extract_chunk_*.json`.

**Why preserve ambiguity?**
The `ambiguities` node type is the formal representation of the
deferred-denouement structure described in the essay above. A text is not
a compressed movie; it is a constraint field that resolves over time.
The `ambiguity_diffusion` and `constraint_dynamics` outputs make that
resolution visible.

**Why typed edges?**
`participates_in`, `causes`, `resolves`, `supports`, `opposes`, `belongs_to`,
`transforms` give the constraint simulator a typed propagation rule for each
edge class. New projection types can be added by writing a single Python
script that queries the graph by node type and edge type.

**Extending the system**
To add a new projection, create `projections/build_<name>.py` that reads
`graph.json` from `sys.argv[1]` and prints JSON to stdout. To add a renderer,
create `render/render_<name>.py`. Add the name to the arrays in
`bin/run_all.sh` and `bin/render_all.sh`.
