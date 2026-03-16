# Text Physics Engine Ecosystem

This directory contains experimental systems exploring how written language can be treated as a structured constraint system rather than as static text.

The core component, Textbot, extracts semantic structure from documents by building a canonical semantic graph and deriving multiple projections from it, including narrative state, causal timelines, rhetorical voice, sonic mappings, and ambiguity diffusion. These projections can be rendered into diagrams, summaries, videos, or other media forms.

Zebra extends this semantic layer into a distributed production architecture. Semantic graphs become task networks that coordinate contributors and computational agents, enabling collaborative assembly of media artifacts through APIs, worker agents, and web interfaces.

The Spherepop script provides a minimal RSVP-style simulation engine that models processes through an event-history architecture. Instead of mutating state directly, the system reconstructs state from an irreversible log of events across scalar, vector, and entropy channels.

Additional modules explore corpus-scale graph construction, wiki generation, and collaborative media pipelines built on the same semantic infrastructure.

Together these components investigate how semantic structure can propagate from raw text into knowledge graphs, distributed workflows, and dynamic simulations.
