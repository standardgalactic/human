#!/usr/bin/env python3
"""generate_scripts.py — convert projection JSON into task-ready script documents.

For each projection type, reads the relevant JSON and emits:
  - One script document per logical unit (scene / module / segment)
  - A task dependency graph across all scripts
  - Downloadable zip bundles per script

Output structure:
    data/scripts/<stem>/
        manifest.json           index of all tasks with metadata
        deps.json               task dependency graph
        <task_id>/
            brief.md
            script.txt
            nodes.json
            style_hints.txt
            dependencies.json
            output_spec.json
        <task_id>.zip           downloadable bundle

Usage:
    python3 src/generate_scripts.py \
        --projections-dir data/projections/<stem> \
        --graph           data/canonical/<stem>/graph.json \
        --output-dir      data/scripts/<stem>
"""

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path


# ── id helpers ────────────────────────────────────────────────────────────────

def task_id(projection_type: str, index: int, label: str) -> str:
    slug = re.sub(r"[^\w]", "_", label.lower())[:30]
    h = hashlib.md5(f"{projection_type}:{index}:{label}".encode()).hexdigest()[:6]
    return f"{projection_type[:6]}_{index:03d}_{slug}_{h}"


# ── difficulty estimator ──────────────────────────────────────────────────────

def estimate_difficulty(duration_s: int, uncertain_count: int, node_count: int) -> str:
    score = duration_s / 30 + uncertain_count * 0.5 + node_count * 0.3
    if score < 3:   return "simple"
    if score < 8:   return "standard"
    return "complex"


# ── output spec by projection type ───────────────────────────────────────────

OUTPUT_SPECS = {
    "narrative_film": {
        "format": "video",
        "aspect_ratio": "16:9",
        "accepted_types": [".mp4", ".webm", ".mov"],
        "notes": "Shot or animation. Preserve textual indeterminacy — do not specify what the source text has not specified.",
    },
    "diagrammatic_structure": {
        "format": "diagram_animation",
        "aspect_ratio": "16:9",
        "accepted_types": [".mp4", ".webm", ".svg", ".png"],
        "notes": "Animated or static diagram. Show typed nodes and edges clearly. Colour by type: blue=entity, orange=event, green=claim.",
    },
    "ambiguity_diffusion": {
        "format": "animation",
        "aspect_ratio": "16:9",
        "accepted_types": [".mp4", ".webm", ".gif"],
        "notes": "Abstract animation showing possibility space collapsing. Early frames: scattered. Late frames: convergent.",
    },
    "rhetorical_voice": {
        "format": "voiceover_or_video",
        "aspect_ratio": "16:9",
        "accepted_types": [".mp4", ".webm", ".mp3", ".wav"],
        "notes": "Spoken argument walkthrough or annotated text display. Highlight rhetorical moves explicitly.",
    },
    "concept_map": {
        "format": "diagram_animation",
        "aspect_ratio": "16:9",
        "accepted_types": [".mp4", ".webm", ".svg", ".png"],
        "notes": "Animated concept cluster. Show themes connecting and reorganizing.",
    },
    "procedural_transform": {
        "format": "screencast_or_animation",
        "aspect_ratio": "16:9",
        "accepted_types": [".mp4", ".webm"],
        "notes": "Step-by-step walkthrough. Show inputs, operations, outputs in sequence.",
    },
    "timeline_causality": {
        "format": "animation",
        "aspect_ratio": "16:9",
        "accepted_types": [".mp4", ".webm", ".png"],
        "notes": "Animated timeline. Events appear in order. Causal arrows appear when effects fire.",
    },
    "character_state": {
        "format": "animation_or_diagram",
        "aspect_ratio": "16:9",
        "accepted_types": [".mp4", ".webm", ".svg"],
        "notes": "Show entity attributes evolving. Radar chart or bar chart update per narrative step.",
    },
    "sonic_mapping": {
        "format": "audio_or_video",
        "aspect_ratio": "16:9",
        "accepted_types": [".mp4", ".webm", ".mp3", ".wav"],
        "notes": "Acoustic realization of semantic tension arc. Tempo from tension, harmony from position.",
    },
    "structural_summary": {
        "format": "diagram_or_video",
        "aspect_ratio": "16:9",
        "accepted_types": [".mp4", ".webm", ".png", ".svg"],
        "notes": "Minimal logical skeleton. Premises → tensions → contradictions → resolutions → open variables.",
    },
}

STYLE_HINTS = {
    "narrative_film":        "Cinematic or illustrated. Preserve ambiguity where the text is underdetermined.",
    "diagrammatic_structure":"Formal, minimal. No decorative elements. Label every edge type.",
    "ambiguity_diffusion":   "Abstract. Dark background. Points scatter and converge.",
    "rhetorical_voice":      "Clear, expository. Text-forward. Emphasis on logical structure.",
    "concept_map":           "Organic layout. Clusters clearly bounded. Connections animated.",
    "procedural_transform":  "Step-by-step. Command-line or whiteboard aesthetic.",
    "timeline_causality":    "Linear or branching timeline. Arrows for causality.",
    "character_state":       "Data-driven. Charts updating in sync with narrative events.",
    "sonic_mapping":         "Atmospheric. Allow silence. Let tension drive dynamics.",
    "structural_summary":    "Diagrammatic. Stark. Logical hierarchy visible at a glance.",
}


# ── script builders per projection type ──────────────────────────────────────

def scripts_from_narrative(proj: dict) -> list[dict]:
    scripts = []
    for i, scene in enumerate(proj.get("scenes", [])):
        chars  = scene.get("characters", [])
        unc    = scene.get("uncertain_details", [])
        dur    = 60 + len(chars) * 15 + len(unc) * 5
        scripts.append({
            "projection_type": "narrative_film",
            "index": i,
            "label": scene.get("summary", f"Scene {i+1}"),
            "duration_estimate_s": dur,
            "script_text": (
                f"SCENE {i+1}\n\n"
                f"Summary: {scene.get('summary', '')}\n\n"
                f"Characters: {', '.join(chars) or 'unspecified'}\n"
                f"Location: {scene.get('location') or 'unspecified'}\n\n"
                f"Actions:\n" +
                "\n".join(f"  - {a}" for a in scene.get("actions", [])) +
                ("\n\nUncertain details (do not invent):\n" +
                 "\n".join(f"  - {u}" for u in unc) if unc else "")
            ),
            "graph_nodes":   [scene.get("scene_id", "")],
            "uncertain_details": unc,
            "textual_basis": scene.get("textual_basis", []),
        })
    return scripts


def scripts_from_diagrammatic(proj: dict) -> list[dict]:
    nodes  = proj.get("nodes", [])
    edges  = proj.get("edges", [])
    # One script for the full graph, one per cluster if clusters exist
    scripts = []
    clusters = proj.get("clusters", [])
    if clusters:
        for i, cluster in enumerate(clusters):
            cluster_nodes = [n for n in nodes if n["id"] in cluster.get("members", [])]
            cluster_edges = [e for e in edges
                             if e["source"] in cluster.get("members", []) or
                                e["target"] in cluster.get("members", [])]
            scripts.append({
                "projection_type": "diagrammatic_structure",
                "index": i,
                "label": f"Cluster: {cluster['label']}",
                "duration_estimate_s": 45 + len(cluster_nodes) * 5,
                "script_text": (
                    f"CLUSTER DIAGRAM: {cluster['label']}\n\n"
                    f"Nodes ({len(cluster_nodes)}):\n" +
                    "\n".join(f"  [{n['type']}] {n['label']}" for n in cluster_nodes[:10]) +
                    f"\n\nEdges ({len(cluster_edges)}):\n" +
                    "\n".join(f"  {e['source']} --{e.get('label','')}→ {e['target']}"
                              for e in cluster_edges[:10])
                ),
                "graph_nodes":   [n["id"] for n in cluster_nodes],
                "uncertain_details": [],
                "textual_basis": [],
            })
    else:
        scripts.append({
            "projection_type": "diagrammatic_structure",
            "index": 0,
            "label": "Full constraint graph",
            "duration_estimate_s": 60 + len(nodes) * 3,
            "script_text": (
                f"CONSTRAINT GRAPH\n\n"
                f"{len(nodes)} nodes, {len(edges)} edges\n\n"
                "Nodes:\n" + "\n".join(f"  [{n.get('type','')}] {n['label']}" for n in nodes[:20]) +
                "\n\nEdges:\n" + "\n".join(f"  {e['source']} --{e.get('label','')}→ {e['target']}"
                                          for e in edges[:20])
            ),
            "graph_nodes":   [n["id"] for n in nodes[:20]],
            "uncertain_details": [],
            "textual_basis": [],
        })
    return scripts


def scripts_from_ambiguity(proj: dict) -> list[dict]:
    units = proj.get("units", [])
    if not units:
        return []
    return [{
        "projection_type": "ambiguity_diffusion",
        "index": 0,
        "label": "Interpretation space collapse",
        "duration_estimate_s": 30 + len(units) * 8,
        "script_text": (
            f"AMBIGUITY DIFFUSION\n\n"
            f"{len(units)} ambiguity nodes — {proj.get('open',0)} open, "
            f"{proj.get('collapsed',0)} resolved\n\n"
            "Sequence:\n" +
            "\n".join(
                f"  Frame {i+1}: [{u.get('status','open')}] {u['label']}"
                f" ({u.get('n_possibilities',0)} possibilities)"
                for i, u in enumerate(units[:10])
            ) +
            f"\n\nFinal resolution: {proj.get('final_resolution', [])}"
        ),
        "graph_nodes":   [u["id"] for u in units],
        "uncertain_details": [u["label"] for u in units if u.get("status") == "open"],
        "textual_basis": [],
    }]


def scripts_from_timeline(proj: dict) -> list[dict]:
    events = proj.get("timeline", [])
    if not events:
        return []
    # Chunk into segments of ~8 events each
    chunk_size = 8
    scripts = []
    for i in range(0, len(events), chunk_size):
        chunk = events[i:i+chunk_size]
        scripts.append({
            "projection_type": "timeline_causality",
            "index": i // chunk_size,
            "label": f"Timeline segment {i // chunk_size + 1}",
            "duration_estimate_s": 20 + len(chunk) * 10,
            "script_text": (
                f"TIMELINE SEGMENT {i // chunk_size + 1}\n"
                f"Events {i+1}–{i+len(chunk)}\n\n" +
                "\n".join(
                    f"  {e['index']}. {e['event']}"
                    + (f"\n     ← {'; '.join(e['causes'][:2])}" if e.get("causes") else "")
                    + (f"\n     → {'; '.join(e['effects'][:2])}" if e.get("effects") else "")
                    for e in chunk
                )
            ),
            "graph_nodes":   [e["event_id"] for e in chunk],
            "uncertain_details": [],
            "textual_basis": [e.get("textual_basis", [""])[0] for e in chunk if e.get("textual_basis")],
        })
    return scripts


def scripts_from_summary(proj: dict) -> list[dict]:
    return [{
        "projection_type": "structural_summary",
        "index": 0,
        "label": "Logical skeleton",
        "duration_estimate_s": 90,
        "script_text": (
            f"STRUCTURAL SUMMARY\n\n"
            f"Premises ({len(proj.get('premises',[]))}):\n" +
            "\n".join(f"  - {p}" for p in proj.get("premises", [])[:5]) +
            f"\n\nOpen variables ({len(proj.get('open_variables',[]))}):\n" +
            "\n".join(f"  - {v}" for v in proj.get("open_variables", [])[:5]) +
            f"\n\nContradictions: {len(proj.get('contradictions',[]))}" +
            f"\n\nResolutions: {len(proj.get('resolutions',[]))}"
        ),
        "graph_nodes":   [],
        "uncertain_details": proj.get("open_variables", [])[:5],
        "textual_basis": [],
    }]


SCRIPT_BUILDERS = {
    "narrative_film":        scripts_from_narrative,
    "diagrammatic_structure":scripts_from_diagrammatic,
    "ambiguity_diffusion":   scripts_from_ambiguity,
    "timeline_causality":    scripts_from_timeline,
    "structural_summary":    scripts_from_summary,
}


def generic_script(proj: dict, projection_type: str) -> list[dict]:
    """Fallback for projection types without a dedicated builder."""
    return [{
        "projection_type": projection_type,
        "index": 0,
        "label": projection_type.replace("_", " ").title(),
        "duration_estimate_s": 90,
        "script_text": f"{projection_type.upper().replace('_',' ')}\n\n" +
                       json.dumps(proj, indent=2, ensure_ascii=False)[:1200],
        "graph_nodes":   [],
        "uncertain_details": [],
        "textual_basis": [],
    }]


# ── dependency inference ──────────────────────────────────────────────────────

def infer_deps(all_scripts: list[dict]) -> list[dict]:
    """Infer task dependencies from shared graph nodes and projection ordering."""
    deps = []
    node_to_tasks: dict[str, list[str]] = {}
    for s in all_scripts:
        for nid in s.get("graph_nodes", []):
            node_to_tasks.setdefault(nid, []).append(s["id"])

    # Tasks sharing a graph node depend on each other (earlier index → dependency)
    for nid, task_ids in node_to_tasks.items():
        ordered = sorted(task_ids)
        for i in range(len(ordered) - 1):
            deps.append({"from": ordered[i], "to": ordered[i + 1], "via": nid})

    # narrative_film scenes are ordered sequentially
    narrative_tasks = sorted(
        [s for s in all_scripts if s["projection_type"] == "narrative_film"],
        key=lambda s: s["index"],
    )
    for i in range(len(narrative_tasks) - 1):
        deps.append({
            "from": narrative_tasks[i]["id"],
            "to":   narrative_tasks[i+1]["id"],
            "via":  "narrative_sequence",
        })

    # Deduplicate
    seen = set()
    unique_deps = []
    for d in deps:
        k = (d["from"], d["to"])
        if k not in seen:
            seen.add(k)
            unique_deps.append(d)

    return unique_deps


# ── betweenness centrality (no networkx dependency) ──────────────────────────

def compute_centrality(task_ids: list[str], deps: list[dict]) -> dict[str, float]:
    """Normalized betweenness centrality via Brandes algorithm."""
    # Build adjacency
    adj: dict[str, list[str]] = {t: [] for t in task_ids}
    for d in deps:
        if d["from"] in adj:
            adj[d["from"]].append(d["to"])
        if d["to"] in adj:
            adj[d["to"]].append(d["from"])

    betweenness = {t: 0.0 for t in task_ids}
    n = len(task_ids)

    for s in task_ids:
        stack, pred, sigma, dist = [], {t: [] for t in task_ids}, {t: 0 for t in task_ids}, {t: -1 for t in task_ids}
        sigma[s] = 1
        dist[s]  = 0
        queue    = [s]
        while queue:
            v = queue.pop(0)
            stack.append(v)
            for w in adj.get(v, []):
                if dist[w] < 0:
                    queue.append(w)
                    dist[w] = dist[v] + 1
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta = {t: 0.0 for t in task_ids}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                if sigma[w]:
                    delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            if w != s:
                betweenness[w] += delta[w]

    # Normalize to [0.5, 2.0] for assembly_weight
    max_b = max(betweenness.values()) if betweenness else 1.0
    if max_b == 0:
        return {t: 1.0 for t in task_ids}
    return {t: 0.5 + 1.5 * (v / max_b) for t, v in betweenness.items()}


# ── bundle writer ─────────────────────────────────────────────────────────────

def write_bundle(script: dict, out_dir: Path) -> None:
    tid  = script["id"]
    tdir = out_dir / tid
    tdir.mkdir(parents=True, exist_ok=True)

    proj_type = script["projection_type"]
    spec      = OUTPUT_SPECS.get(proj_type, {})
    hint      = STYLE_HINTS.get(proj_type, "")

    # brief.md
    brief = f"""# {script['label']}

**Task ID:** `{tid}`
**Projection:** {proj_type}
**Difficulty:** {script['difficulty']}
**Estimated duration:** {script['duration_estimate_s']}s
**Assembly weight:** {script.get('assembly_weight', 1.0):.2f}

## Script

{script['script_text']}

## Style notes

{hint}

## Output requirements

- Format: {spec.get('format', 'video')}
- Aspect ratio: {spec.get('aspect_ratio', '16:9')}
- Accepted file types: {', '.join(spec.get('accepted_types', ['.mp4']))}
- Notes: {spec.get('notes', '')}
"""
    (tdir / "brief.md").write_text(brief, encoding="utf-8")
    (tdir / "script.txt").write_text(script["script_text"], encoding="utf-8")
    (tdir / "nodes.json").write_text(
        json.dumps({"graph_nodes": script["graph_nodes"],
                    "textual_basis": script.get("textual_basis", [])},
                   indent=2), encoding="utf-8"
    )
    (tdir / "style_hints.txt").write_text(hint, encoding="utf-8")
    (tdir / "dependencies.json").write_text(
        json.dumps({"task_id": tid, "depends_on": script.get("depends_on", [])}, indent=2),
        encoding="utf-8",
    )
    (tdir / "output_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")

    # zip bundle
    zip_path = out_dir / f"{tid}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in tdir.iterdir():
            zf.write(f, arcname=f"task_{tid}/{f.name}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--projections-dir", required=True)
    ap.add_argument("--graph",           required=True)
    ap.add_argument("--output-dir",      required=True)
    args = ap.parse_args()

    proj_dir = Path(args.projections_dir)
    out_dir  = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_scripts: list[dict] = []

    for proj_file in sorted(proj_dir.glob("*.json")):
        try:
            proj = json.loads(proj_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        proj_type = proj_file.stem
        builder   = SCRIPT_BUILDERS.get(proj_type, None)
        raw       = builder(proj) if builder else generic_script(proj, proj_type)

        for raw_s in raw:
            spec = OUTPUT_SPECS.get(proj_type, {})
            diff = estimate_difficulty(
                raw_s["duration_estimate_s"],
                len(raw_s.get("uncertain_details", [])),
                len(raw_s.get("graph_nodes", [])),
            )
            tid = task_id(proj_type, raw_s["index"], raw_s["label"])
            script = {
                "id":                  tid,
                "projection_type":     proj_type,
                "index":               raw_s["index"],
                "label":               raw_s["label"],
                "duration_estimate_s": raw_s["duration_estimate_s"],
                "difficulty":          diff,
                "assembly_weight":     1.0,   # updated below
                "script_text":         raw_s["script_text"],
                "graph_nodes":         raw_s.get("graph_nodes", []),
                "uncertain_details":   raw_s.get("uncertain_details", []),
                "textual_basis":       raw_s.get("textual_basis", []),
                "output_spec":         spec,
                "style_hint":          STYLE_HINTS.get(proj_type, ""),
                "depends_on":          [],
            }
            all_scripts.append(script)

    # Infer dependencies and compute centrality
    deps = infer_deps(all_scripts)
    task_ids = [s["id"] for s in all_scripts]
    centrality = compute_centrality(task_ids, deps)

    dep_targets: dict[str, list[str]] = {s["id"]: [] for s in all_scripts}
    for d in deps:
        if d["to"] in dep_targets:
            dep_targets[d["to"]].append(d["from"])

    for script in all_scripts:
        script["assembly_weight"] = round(centrality.get(script["id"], 1.0), 3)
        script["depends_on"]      = dep_targets.get(script["id"], [])

    # Write bundles
    for script in all_scripts:
        write_bundle(script, out_dir)

    # Write manifest and deps
    manifest = {
        "total_tasks": len(all_scripts),
        "tasks": [
            {k: v for k, v in s.items() if k != "script_text"}
            for s in all_scripts
        ],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "deps.json").write_text(
        json.dumps({"dependencies": deps}, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Generated {len(all_scripts)} task scripts → {out_dir}")
    print(f"  manifest: {out_dir}/manifest.json")
    print(f"  deps:     {out_dir}/deps.json")


if __name__ == "__main__":
    main()
