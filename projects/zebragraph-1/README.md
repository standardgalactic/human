# zebragraph

*A predation-resistant text analysis engine.*

Reads a text, builds one canonical semantic graph, and projects it into ten
structurally distinct interpretive outputs: film storyboard, constraint
diagram, ambiguity diffusion animation, concept field, timeline, character
states, sonic arc, procedural steps, rhetorical structure, and logical
skeleton.

The LLM is called exactly once (canonical extraction).
Everything downstream is deterministic Python.

---

## Philosophy

Most text-to-media systems are interpretive predators. They collapse a text
into a single realization immediately: the variable "traveler" becomes a
specific face, voice, age, and costume before the narrative has supplied
those constraints. The interpretation space is reduced to one target as fast
as possible.

Zebra takes the opposite position.

The canonical semantic graph is a predation-resistant field. Ambiguity nodes
are not extraction failures — they are first-class objects recording the
text's own underdetermination. An entity's `uncertain` attribute list is not
a gap to be filled. It is the formal statement that the text has not licensed
that interpretation, and that filling it prematurely is an act imposed on the
text rather than derived from it.

The projection architecture preserves the herd. Ten structurally distinct
outputs — film, graph, diffusion, timeline, sonic, procedural, and others —
show different patterns in the same constraint field. None claims to be the
canonical rendering, because texts do not have canonical renderings. They
have constraint structures that can be projected into many spaces.

The constraint simulator is the Turing-pattern layer. Meaning does not arrive
from a central blueprint. It emerges through local propagation: events fire,
activation spreads along typed edges, ambiguity nodes collapse when enough
constraints accumulate. The stripe pattern of a zebra is not designed from
outside — it emerges from reaction-diffusion dynamics internal to the
developmental field. The semantic structure of a text works the same way.

A generative media system hunts the text and captures one interpretation.
Zebra lets the interpretation remain a patterned herd until the text itself
supplies the constraints to resolve it.

---

## Install

```bash
git clone <repo>
cd zebragraph

# Required Python packages
pip install requests matplotlib networkx

# Optional — real semantic embeddings for concept_diffusion
pip install sentence-transformers scikit-learn

# Optional — MIDI output from sonic renderer
pip install pretty_midi

# ffmpeg — compiles frame sequences into MP4
# macOS:   brew install ffmpeg
# Debian:  apt-get install ffmpeg

# Ollama — local LLM server (https://ollama.com)
ollama pull granite4
ollama serve          # must be running for 'zebra extract'

# Make the CLI available on your PATH (optional)
ln -s "$(pwd)/zebra" /usr/local/bin/zebra
```

---

## Usage

```
zebra extract <file>
zebra project <name|all>   [--stem STEM]
zebra render  <name|all>   [--stem STEM]
zebra simulate constraints [--stem STEM]
```

`--stem` overrides the name derived from the input filename.
If omitted, zebra uses the most recently extracted file.

---

## Quickstart

```bash
zebra extract essay.txt
zebra project ambiguity
zebra render diffusion
zebra simulate constraints
```

Or run everything at once:

```bash
zebra extract essay.txt
zebra project all
zebra render all
```

Outputs land in:

```
data/canonical/essay/graph.json      ← canonical semantic graph
data/projections/essay/*.json        ← ten projection files
data/videos/                         ← PNG and MP4 outputs
```

---

## Projection names

| Short alias   | Full name               | What it produces                          |
|---------------|-------------------------|-------------------------------------------|
| `narrative`   | `narrative_film`        | Scene list with characters, uncertainties |
| `diagram`     | `diagrammatic_structure`| Typed node/edge constraint graph          |
| `ambiguity`   | `ambiguity_diffusion`   | Interpretation space collapsing to denouement |
| `rhetoric`    | `rhetorical_voice`      | Claim structure, stances, oppositions     |
| `concepts`    | `concept_map`           | Thematic clusters and connections         |
| `procedural`  | `procedural_transform`  | Text as ordered state-change operations   |
| `timeline`    | `timeline_causality`    | Causal event spine                        |
| `characters`  | `character_state`       | Entity state vectors across narrative time|
| `sonic`       | `sonic_mapping`         | Tempo, tension, harmonic arc              |
| `summary`     | `structural_summary`    | Premises, contradictions, open variables  |

---

## Render names

| Short alias   | Full name               | Output                        |
|---------------|-------------------------|-------------------------------|
| `diagram`     | `diagrammatic_structure`| graph PNG                     |
| `diffusion`   | `ambiguity_diffusion`   | animated MP4                  |
| `concept`     | `concept_diffusion`     | animated MP4                  |
| `constraints` | `constraint_dynamics`   | animated MP4                  |
| `timeline`    | `timeline_causality`    | timeline PNG                  |
| `characters`  | `character_state`       | small-multiples PNG           |
| `sonic`       | `sonic_mapping`         | tension arc PNG + optional MIDI |
| `film`        | `narrative_film`        | storyboard MP4                |
| `summary`     | `structural_summary`    | logical skeleton PNG          |

---

## Change model

```bash
MODEL=llama3.2 zebra extract essay.txt
# or
zebra extract essay.txt --model llama3.2
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

## Design notes

**Why one LLM call?**
Concentrating uncertainty in a single extraction step makes the rest of the
system transparent and debuggable. If a projection looks wrong, the place to
look is `data/analyses/<stem>/canonical_extract_chunk_*.json`.

**Why preserve ambiguity?**
The `ambiguities` node type is the formal representation of the
deferred-denouement structure. A text is not a compressed movie; it is a
constraint field that resolves over time. The `ambiguity_diffusion` and
`constraint_dynamics` outputs make that resolution visible.

**Why typed edges?**
`participates_in`, `causes`, `resolves`, `supports`, `opposes`, `belongs_to`,
`transforms` give the constraint simulator a typed propagation rule for each
edge class.

**Extending the system**
To add a new projection, create `projections/build_<myname>.py` that reads
`graph.json` from `sys.argv[1]` and prints JSON to stdout. To add a renderer,
create `render/render_<myname>.py`. Register the alias in the `PROJECTION_ALIASES`
and `RENDER_ALIASES` tables inside `zebra`, and add the full name to
`ALL_PROJECTIONS` / `ALL_RENDERS`. Then:

```bash
zebra project myname
zebra render  myname
```
