# textbot

A text-analysis and multi-modal rendering pipeline.

Treats any text as a **constraint system resolving over time** rather than a
single fixed representation. Produces ten orthogonal projections of the same
semantic structure, each renderable as a distinct visual or audio artefact.

---

## Conceptual Architecture

```
text
 └─ chunking
     └─ canonical extraction  (LLM → JSON semantic graph)
         └─ ten projection builders  (deterministic Python)
             └─ ten renderers  (matplotlib / ffmpeg / ImageMagick)
                 └─ videos/, images/
```

The **canonical semantic graph** is the central object. It encodes:

- `entities` — named or implied agents, objects, systems
- `events` — state changes with participants and causal links
- `relations` — typed edges between any nodes
- `claims` — explicit argumentative propositions
- `ambiguities` — underspecified elements with possibility fields
- `transformations` — operations mapping one state to another
- `timeline` — ordered event sequence
- `themes` — conceptual clusters

All projections are deterministic transformations of this graph.
The LLM is invoked only once, during canonical extraction.

---

## Directory Layout

```
textbot/
  bin/
    run_all.sh              — run all 11 analysis categories on one file
    run_one.sh              — run one category
    run_canonical.sh        — extract canonical graph only
    run_projection.sh       — build one projection from canonical graph
    render_all.sh           — render all projections to videos/

  src/
    chunk_text.py           — paragraph-preserving chunker
    call_ollama.py          — Ollama API wrapper (temperature 0)
    merge_chunks.py         — merge per-chunk JSON outputs
    validate_json.py        — JSON validity check
    build_canonical_graph.py — merge chunk graphs, deduplicate
    constraint_simulator.py — simulate activation propagation

  prompts/
    canonical_extract.txt   — base semantic graph prompt
    narrative_film.txt
    diagrammatic_structure.txt
    ambiguity_diffusion.txt
    rhetorical_voice.txt
    concept_map.txt
    procedural_transform.txt
    timeline_causality.txt
    character_state.txt
    sonic_mapping.txt
    structural_summary.txt

  projections/
    build_narrative_film.py
    build_diagrammatic_structure.py
    build_ambiguity_diffusion.py
    build_concept_map.py
    build_procedural_transform.py
    build_timeline_causality.py
    build_character_state.py
    build_sonic_mapping.py
    build_rhetorical_voice.py
    build_structural_summary.py

  render/
    render_narrative_film.py
    render_diagrammatic_structure.py
    render_ambiguity_diffusion.py        ← animated mp4
    render_concept_map.py
    render_timeline_causality.py
    render_character_state.py
    render_sonic_mapping.py
    render_procedural_transform.py
    render_rhetorical_voice.py
    render_structural_summary.py
    render_constraint_dynamics.py        ← animated mp4
    render_concept_diffusion_field.py    ← animated mp4 (requires sentence-transformers)

  data/
    input/      — place your .txt files here
    chunks/     — auto-generated
    analyses/   — per-chunk JSON
    canonical/  — merged canonical graphs
    projections/— per-category projection JSON
    videos/     — rendered outputs

  index.html    — standalone project generator (no server required)
```

---

## Dependencies

**System**
- `ffmpeg` — video assembly
- `imagemagick` — frame generation for narrative_film renderer

**Python**
```
pip install requests networkx matplotlib numpy
```

**Optional (for concept diffusion field renderer)**
```
pip install sentence-transformers scikit-learn
```

**Ollama**
- Install from https://ollama.com
- Pull a Granite 4 model: `ollama pull granite4`
- Verify it is running: `ollama serve`

---

## Quick Start

```bash
# 1. Place your text file
cp myessay.txt data/input/

# 2. Extract canonical graph
bin/run_canonical.sh data/input/myessay.txt

# 3. Build all projections
STEM=myessay
GRAPH="data/canonical/$STEM/graph.json"
mkdir -p data/projections/$STEM

for P in narrative_film diagrammatic_structure ambiguity_diffusion \
         concept_map procedural_transform timeline_causality \
         character_state sonic_mapping rhetorical_voice structural_summary; do
  bin/run_projection.sh "$P" "$GRAPH" "data/projections/$STEM/${P}.json"
done

# 4. Render all
bin/render_all.sh data/projections/$STEM
```

Outputs appear in `videos/`.

---

## Projection Categories

| Category | What it shows |
|---|---|
| `narrative_film` | Events as cinematic scenes |
| `diagrammatic_structure` | Entities and relations as typed graph |
| `ambiguity_diffusion` | Possibility fields collapsing to resolution |
| `concept_map` | Thematic clusters and connections |
| `procedural_transform` | Text as state-machine / workflow |
| `timeline_causality` | Events ordered with causal links |
| `character_state` | Entity attributes evolving over time |
| `sonic_mapping` | Semantic tension mapped to acoustic parameters |
| `rhetorical_voice` | Argument structure and claim types |
| `structural_summary` | Premises, definitions, open variables |

Plus two derived renderers:
- `render_constraint_dynamics.py` — activation propagation animation
- `render_concept_diffusion_field.py` — semantic embedding field animation

---

## Model Configuration

The default model is `granite4`. Override with the `MODEL` environment variable:

```bash
MODEL=llama3 bin/run_canonical.sh data/input/myessay.txt
```

All prompts use `temperature: 0` for deterministic structured output.

---

## Project Generator

Open `index.html` in any browser. Each visitor receives a deterministic set of
project suggestions derived from a locally-stored seed. The seed is stable across
page loads; clicking **New Assignment** generates a fresh seed.

Uses FNV-1a hashing and Knuth multiplicative offset to select from combinatorial
vocabulary arrays. Frameworks reference RSVP, Spherepop, TARTAN, and related
theoretical structures.

---

## Design Notes

- The LLM is only invoked during canonical extraction. All projections are
  deterministic Python transformations of the resulting graph.
- `explicit_textual_basis` fields throughout the schema anchor every node and
  edge to a specific phrase in the source text, preventing hallucinated structure.
- Ambiguity nodes are first-class citizens. Underspecification is preserved
  rather than resolved prematurely.
- The `constraint_simulator` treats the timeline as a sequence of activation
  events, propagating influence along typed relation edges. This implements
  the "deferred denouement" model: meaning stabilises gradually.
