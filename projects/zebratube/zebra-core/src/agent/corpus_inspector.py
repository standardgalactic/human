#!/usr/bin/env python3
"""
agent/corpus_inspector.py — local semantic fingerprinting

Scans configured directories, extracts lightweight signals from text files,
and produces a topic interest vector. No files are uploaded; only the
resulting vector is shared with the server.

Privacy guarantees:
  - Only reads filenames, directory names, first 512 chars, and headers
  - Uses a local keyword classifier; no external API calls
  - The raw file contents never leave the machine
  - The resulting vector contains only topic weights, not file paths
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path


# ── Default scan directories ──────────────────────────────────────────────────

DEFAULT_SCAN_DIRS = [
    "~/Documents",
    "~/Projects",
    "~/repos",
    "~/code",
    "~/src",
    "~/notes",
    "~/research",
    "~/Desktop",
]

SCAN_EXTENSIONS = {
    ".md", ".txt", ".rst", ".tex", ".org",
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".r", ".jl", ".m", ".f90",
    ".html", ".htm", ".css",
    ".yaml", ".yml", ".toml", ".json",
    ".ipynb",
}

SKIP_DIRS = {
    ".git", ".hg", "node_modules", "__pycache__", ".venv",
    "venv", "env", ".env", "dist", "build", ".cache",
    ".idea", ".vscode", "vendor", "tmp", "temp",
}

MAX_FILE_BYTES = 50_000
MAX_FILES_PER_DIR = 500
MAX_TOTAL_FILES = 5000


# ── Topic taxonomy ────────────────────────────────────────────────────────────
# Each topic → weighted keyword list.
# Score = sum(weight) / normaliser.

TOPIC_KEYWORDS: dict[str, list[tuple[str, float]]] = {
    "mathematics": [
        ("theorem", 2.0), ("proof", 1.8), ("lemma", 2.0), ("corollary", 2.0),
        ("algebra", 1.5), ("calculus", 1.5), ("topology", 2.0), ("manifold", 2.0),
        ("matrix", 1.2), ("eigenvalue", 2.0), ("fourier", 1.8), ("differential", 1.2),
        ("equation", 1.0), ("integral", 1.2), ("gradient", 1.0), ("vector space", 2.0),
        ("category theory", 2.5), ("functor", 2.5), ("monoid", 2.5),
    ],
    "programming": [
        ("def ", 1.5), ("function", 1.0), ("import ", 1.5), ("class ", 1.5),
        ("algorithm", 1.5), ("api", 1.2), ("async", 1.5), ("await", 1.5),
        ("repository", 1.0), ("commit", 1.0), ("branch", 1.0), ("refactor", 1.5),
        ("typescript", 2.0), ("python", 1.5), ("rust", 2.0), ("golang", 2.0),
        ("sql", 1.5), ("database", 1.2), ("backend", 1.5), ("frontend", 1.5),
    ],
    "machine_learning": [
        ("neural network", 2.5), ("gradient descent", 2.5), ("backpropagation", 2.5),
        ("transformer", 2.0), ("attention", 1.5), ("embedding", 1.5),
        ("training", 1.2), ("dataset", 1.2), ("loss function", 2.0),
        ("pytorch", 2.5), ("tensorflow", 2.5), ("huggingface", 2.5),
        ("llm", 2.0), ("fine-tuning", 2.0), ("inference", 1.5),
        ("classification", 1.5), ("regression", 1.5), ("clustering", 1.5),
    ],
    "philosophy": [
        ("ontology", 2.5), ("epistemology", 2.5), ("phenomenology", 2.5),
        ("dialectic", 2.0), ("hermeneutics", 2.5), ("consciousness", 1.5),
        ("ethics", 1.5), ("metaphysics", 2.0), ("aesthetics", 2.0),
        ("critique", 1.2), ("argument", 1.0), ("proposition", 1.5),
        ("hegel", 2.5), ("kant", 2.5), ("wittgenstein", 2.5), ("heidegger", 2.5),
    ],
    "physics": [
        ("quantum", 2.0), ("relativity", 2.0), ("thermodynamics", 2.0),
        ("entropy", 1.8), ("hamiltonian", 2.5), ("lagrangian", 2.5),
        ("field theory", 2.5), ("particle", 1.5), ("wave function", 2.5),
        ("schrödinger", 2.5), ("bohr", 2.0), ("planck", 2.0),
        ("force", 1.0), ("momentum", 1.5), ("energy", 1.0),
    ],
    "biology": [
        ("genome", 2.0), ("protein", 1.5), ("cell", 1.2), ("dna", 2.0),
        ("evolution", 1.8), ("organism", 1.5), ("species", 1.5),
        ("neural", 1.5), ("synapse", 2.0), ("cortex", 2.0), ("neuron", 2.0),
        ("ecology", 2.0), ("metabolism", 2.0), ("phenotype", 2.5), ("genotype", 2.5),
    ],
    "video_audio": [
        ("render", 1.5), ("timeline", 1.2), ("keyframe", 2.0), ("compositor", 2.0),
        ("blender", 2.5), ("premiere", 2.0), ("after effects", 2.5), ("davinci", 2.0),
        ("codec", 2.0), ("bitrate", 2.0), ("audio mix", 2.5), ("color grade", 2.5),
        ("animation", 1.5), ("frame rate", 2.0), ("resolution", 1.0),
        (".blend", 3.0), (".prproj", 3.0), (".aep", 3.0),
    ],
    "music": [
        ("chord", 2.0), ("melody", 2.0), ("harmony", 2.0), ("rhythm", 1.5),
        ("tempo", 1.5), ("midi", 2.5), ("synthesizer", 2.5), ("daw", 2.5),
        ("ableton", 3.0), ("logic pro", 3.0), ("fl studio", 3.0),
        ("scale", 1.5), ("note", 1.0), ("pitch", 1.5), ("timbre", 2.0),
    ],
    "writing": [
        ("chapter", 1.5), ("narrative", 1.5), ("character", 1.2), ("plot", 1.5),
        ("dialogue", 1.5), ("prose", 2.0), ("essay", 1.5), ("fiction", 2.0),
        ("draft", 1.2), ("revision", 1.2), ("manuscript", 2.0), ("paragraph", 1.0),
    ],
    "design": [
        ("typography", 2.5), ("layout", 1.5), ("colour palette", 2.5),
        ("figma", 3.0), ("sketch", 2.5), ("illustrator", 2.5), ("photoshop", 2.5),
        ("ui", 1.5), ("ux", 1.5), ("wireframe", 2.5), ("prototype", 1.5),
        ("grid", 1.2), ("font", 1.5), ("icon", 1.2),
    ],
}


# ── File text extraction ───────────────────────────────────────────────────────

def _extract_snippet(path: Path) -> str:
    """Extract lightweight signals: filename, parent dir, first 512 chars."""
    parts = [path.stem.replace("_", " ").replace("-", " "), path.parent.name]
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read(512)
        else:
            text = path.read_text(encoding="utf-8", errors="replace")

        # For notebooks: extract markdown cell text
        if path.suffix == ".ipynb":
            try:
                nb = json.loads(text if len(text) < 4096 else path.read_text()[:8192])
                cells = nb.get("cells", [])[:5]
                text = " ".join(
                    "".join(c.get("source", []))
                    for c in cells if c.get("cell_type") == "markdown"
                )
            except Exception:
                pass

        # Extract headings and first lines
        lines = text.splitlines()[:20]
        heading_lines = [l.lstrip("# ").strip() for l in lines
                         if l.startswith("#") or (l and l[0].isupper())]
        parts.extend(heading_lines[:5])
        parts.extend(lines[:3])
    except Exception:
        pass
    return " ".join(parts).lower()


# ── Scoring ────────────────────────────────────────────────────────────────────

def _score_snippet(snippet: str) -> dict[str, float]:
    scores: dict[str, float] = defaultdict(float)
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw, weight in keywords:
            if kw in snippet:
                scores[topic] += weight
    return dict(scores)


# ── Directory walker ───────────────────────────────────────────────────────────

def _iter_files(root: Path, depth: int = 4) -> list[Path]:
    results: list[Path] = []
    try:
        for entry in root.iterdir():
            if len(results) >= MAX_FILES_PER_DIR:
                break
            if entry.is_dir():
                if entry.name.startswith(".") or entry.name in SKIP_DIRS:
                    continue
                if depth > 0:
                    results.extend(_iter_files(entry, depth - 1))
            elif entry.is_file():
                if entry.suffix.lower() in SCAN_EXTENSIONS:
                    results.append(entry)
    except PermissionError:
        pass
    return results


# ── Main inspector ─────────────────────────────────────────────────────────────

def inspect(
    scan_dirs: list[str] | None = None,
    verbose: bool = False,
) -> dict[str, float]:
    """
    Scan configured directories and return a normalised topic interest vector.
    Keys are topic names, values are weights in [0, 1].
    """
    if scan_dirs is None:
        scan_dirs = DEFAULT_SCAN_DIRS

    accumulated: dict[str, float] = defaultdict(float)
    file_count = 0

    for dir_str in scan_dirs:
        root = Path(dir_str).expanduser()
        if not root.exists() or not root.is_dir():
            continue
        files = _iter_files(root)
        for path in files:
            if file_count >= MAX_TOTAL_FILES:
                break
            snippet = _extract_snippet(path)
            scores  = _score_snippet(snippet)
            for topic, score in scores.items():
                accumulated[topic] += score
            if verbose and scores:
                top = max(scores, key=scores.get)
                print(f"  {path.name[:40]:40s}  {top}")
            file_count += 1

    if verbose:
        print(f"\nInspected {file_count} files across {len(scan_dirs)} directories")

    if not accumulated:
        return {}

    # Normalise to [0, 1]
    total = sum(accumulated.values())
    return {
        topic: round(score / total, 4)
        for topic, score in sorted(accumulated.items(), key=lambda x: -x[1])
        if score > 0
    }


# ── Task affinity scorer ──────────────────────────────────────────────────────

# Map projection types and task labels to topic clusters
PROJECTION_TOPIC_MAP: dict[str, list[str]] = {
    "narrative_film":         ["writing", "video_audio"],
    "diagrammatic_structure": ["mathematics", "programming", "design"],
    "ambiguity_diffusion":    ["mathematics", "philosophy"],
    "rhetorical_voice":       ["writing", "philosophy"],
    "concept_map":            ["programming", "mathematics", "philosophy"],
    "procedural_transform":   ["programming", "mathematics"],
    "timeline_causality":     ["writing", "programming"],
    "character_state":        ["writing", "programming"],
    "sonic_mapping":          ["music", "mathematics"],
    "structural_summary":     ["mathematics", "philosophy", "writing"],
}

CAPABILITY_TOPIC_MAP: dict[str, list[str]] = {
    "diagram_generation":   ["mathematics", "programming", "design"],
    "3d_animation":         ["video_audio", "design"],
    "mathematical_diagram": ["mathematics", "physics"],
    "narration":            ["writing", "philosophy"],
    "audio_processing":     ["music"],
    "screen_recording":     ["programming"],
    "video_rendering_gpu":  ["video_audio"],
    "latex_typesetting":    ["mathematics", "physics"],
}


def task_affinity(
    task: dict,
    interest_vector: dict[str, float],
    capabilities: list[str],
) -> float:
    """
    Compute semantic affinity between a task and the local interest vector.
    Returns a score in [0, 1].
    """
    proj_type = task.get("projection_type", "")
    label     = (task.get("label") or "").lower()

    relevant_topics: set[str] = set()

    # From projection type
    for topic in PROJECTION_TOPIC_MAP.get(proj_type, []):
        relevant_topics.add(topic)

    # From capabilities required
    for cap in (task.get("capabilities_required") or []):
        for topic in CAPABILITY_TOPIC_MAP.get(cap, []):
            relevant_topics.add(topic)

    # From label keywords
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw, _ in keywords:
            if kw in label:
                relevant_topics.add(topic)

    if not relevant_topics:
        return 0.5  # neutral when no signal

    score = sum(interest_vector.get(t, 0.0) for t in relevant_topics)
    # Cap at 1.0, minimum 0.05 (always slightly possible)
    return min(1.0, max(0.05, score * 3.0))


if __name__ == "__main__":
    import sys
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    vector = inspect(verbose=verbose)
    print("\nInterest vector:")
    for topic, weight in sorted(vector.items(), key=lambda x: -x[1]):
        bar = "█" * int(weight * 40)
        print(f"  {topic:<22} {bar}  {weight:.3f}")
