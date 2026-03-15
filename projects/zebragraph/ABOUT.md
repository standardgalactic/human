# zebragraph — about

---

## Tagline

A predation-resistant text analysis engine: preserves interpretive
indeterminacy until the text itself supplies the constraints to resolve it.

---

## One-paragraph abstract

Zebragraph is a text analysis engine built around a single philosophical
commitment: a written text is not a compressed film but a constraint field,
and premature collapse of that field into a single audiovisual realization
destroys the structural information that makes the text what it is. The system
extracts one canonical semantic graph from a text — encoding entities, events,
claims, ambiguities, transformations, and themes as typed nodes with explicit
underdetermination preserved — and then projects that graph into ten
structurally distinct outputs without ever asserting that any one of them is
the canonical interpretation. The architecture takes its name and its
conceptual stance from zebra biology: where generative media systems behave as
interpretive predators that lock onto a single target immediately, zebragraph
maintains the patterned herd, using reaction-diffusion-style constraint
propagation to let meaning emerge from the text's own internal structure
rather than from an imposed rendering decision.

---

## Extended description

### The problem

When a generative video or image system processes the sentence "a traveler
enters a room," it must immediately resolve every visual parameter: age,
gender, appearance, voice, lighting, architecture, period. The moment it
renders, the interpretation space collapses to one target. This is not a
limitation of current models — it is a structural consequence of the
commitment to produce a single output. Written language does not work this
way. The variable "traveler" in that sentence functions more like a
mathematical placeholder than like a described person: its properties are
gradually constrained as the narrative progresses, and the meaning of the
text partly consists in the sequence and nature of those constraints.
Forcing immediate resolution destroys that sequence.

### The stance

Zebragraph treats the text as a partially specified constraint system and
treats premature resolution as an interpretive imposition. The canonical
semantic graph stores ambiguity as a first-class node type. An entity's
`uncertain` attribute list — `age`, `voice`, `appearance` — is not a gap
to be filled but a formal record of what the text has not licensed. The
`ambiguity_diffusion` projection tracks how those open variables narrow over
the course of a narrative, making the deferred-denouement structure of
written language visible rather than silently collapsing it.

### The architecture

The system has three stages. In the extraction stage, the text is chunked
along paragraph boundaries and sent to a local language model (Ollama,
defaulting to Granite 4 at temperature zero) with a single structured prompt
that extracts the canonical graph. This is the only point where a language
model is called. In the projection stage, ten deterministic Python scripts
read the graph and each emit a different JSON structure foregrounding a
different aspect of the constraint network: narrative scenes, typed graphs,
ambiguity collapse sequences, rhetorical argument structure, thematic
clusters, procedural operations, causal timelines, entity state vectors,
acoustic parameters, and logical skeletons. In the rendering stage, nine
renderers convert those JSON structures into static PNGs or animated MP4s.
The constraint simulator, which models activation propagating along typed
edges as narrative events fire, underlies both the `constraint_dynamics`
renderer and the `sonic_mapping` projection's tension calculations.

### The name

Zebra stripes are a canonical example of Turing-pattern formation: structure
emerging from local reaction-diffusion dynamics across a developmental field
rather than from a central blueprint. In herd motion, the stripes produce
what biologists call motion dazzle or confusion camouflage — the predator's
targeting system breaks down because the individual body dissolves into the
patterned field. Both properties map directly onto the system's design.
Meaning in zebragraph emerges through constraint propagation across a typed
relational field, not from an authoritative external rendering. And the
system resists interpretive targeting by refusing to present a single
isolated realization, offering instead a structured field of projections
from which no single one claims canonical status.

The name also operates as a rhetorical counterweight in the space of AI tool
naming. Where names like Moltbook or OpenClaw encode predation, extraction,
and transformation — positioning the tool as an agent acting on text — Zebra
positions the tool as a field-preserving observer. The text is not prey.

---

## CLI summary

```
zebra extract <file>                 build canonical semantic graph
zebra project <name|all>            project graph into interpretive JSON
zebra render  <name|all>            render projection to PNG or MP4
zebra simulate constraints          run constraint propagation simulator
```

Projection names: `narrative`, `diagram`, `ambiguity`, `rhetoric`,
`concepts`, `procedural`, `timeline`, `characters`, `sonic`, `summary`

Render names: `diagram`, `diffusion`, `concept`, `constraints`,
`timeline`, `characters`, `sonic`, `film`, `summary`
