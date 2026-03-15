#!/usr/bin/env python3
"""
agent/scorer.py — task ranking for the local Zebra agent

Combines three signals into a final task score:

    score(task) =
        capability_match(node, task)
        × semantic_affinity(task, interest_vector)
        × scarcity(task)
        × assembly_weight(task)

Each factor is in [0, 1] or [0.5, 2.0] for assembly_weight.
The product gives a total in [0, ~2].
"""

import math
from dataclasses import dataclass
from typing import Any


# ── Output format → required capabilities ─────────────────────────────────────

FORMAT_CAPABILITY_REQUIREMENTS: dict[str, list[str]] = {
    "video":             ["video_rendering_cpu", "video_rendering_gpu", "screen_recording"],
    "video_rendering_gpu": ["gpu_rendering", "video_rendering_gpu"],
    "animation":         ["3d_animation", "diagram_generation", "video_rendering_cpu"],
    "diagram_animation": ["diagram_generation", "video_rendering_cpu"],
    "diagram":           ["diagram_generation", "vector_graphics"],
    "audio":             ["narration", "audio_processing"],
    "voiceover":         ["narration"],
    "screencast":        ["screen_recording"],
    "screencast_or_animation": ["screen_recording", "diagram_generation"],
    "voiceover_or_video":      ["narration", "video_rendering_cpu"],
    "audio_or_video":          ["narration", "video_rendering_cpu"],
}

# Projection types that benefit strongly from specific capabilities
PROJECTION_PREFERRED_CAPS: dict[str, list[str]] = {
    "narrative_film":         ["video_rendering_gpu", "3d_animation"],
    "diagrammatic_structure": ["diagram_generation", "mathematical_diagram"],
    "ambiguity_diffusion":    ["diagram_generation", "video_rendering_cpu"],
    "sonic_mapping":          ["audio_processing", "narration"],
    "structural_summary":     ["diagram_generation", "latex_typesetting"],
    "procedural_transform":   ["screen_recording"],
    "rhetorical_voice":       ["narration"],
}


# ── Difficulty → minimum resource thresholds ──────────────────────────────────

DIFFICULTY_REQUIREMENTS = {
    "simple":   {"ram_gb": 4,  "cpu_cores": 2},
    "standard": {"ram_gb": 8,  "cpu_cores": 4},
    "complex":  {"ram_gb": 16, "cpu_cores": 8},
}


# ── Scoring ────────────────────────────────────────────────────────────────────

@dataclass
class TaskScore:
    task_id:            str
    label:              str
    projection_type:    str
    capability_match:   float   # [0, 1]
    semantic_affinity:  float   # [0, 1]
    scarcity:           float   # [0, 1]
    assembly_weight:    float   # [0.5, 2.0]
    total:              float   # product of all factors
    bounty:             float
    reasons:            list[str]


def capability_match(
    task: dict,
    capabilities: list[str],
    ram_gb: float,
    cpu_cores: int,
    has_gpu: bool,
) -> tuple[float, list[str]]:
    """
    Score [0, 1] representing how well the node can execute this task.
    Also returns list of reason strings for display.
    """
    reasons: list[str] = []
    score = 0.0
    weight_sum = 0.0

    proj_type   = task.get("projection_type", "")
    output_fmt  = (task.get("output_spec") or {}).get("format", "video")
    difficulty  = task.get("difficulty", "standard")

    # Check minimum hardware
    hw_req = DIFFICULTY_REQUIREMENTS.get(difficulty, DIFFICULTY_REQUIREMENTS["standard"])
    if ram_gb < hw_req["ram_gb"]:
        reasons.append(f"⚠ RAM: need {hw_req['ram_gb']}GB, have {ram_gb}GB")
        return 0.0, reasons
    if cpu_cores < hw_req["cpu_cores"]:
        reasons.append(f"⚠ CPU: need {hw_req['cpu_cores']} cores, have {cpu_cores}")
        return 0.05, reasons

    # Check output format capabilities (hard requirement, weighted 0.5)
    fmt_caps = FORMAT_CAPABILITY_REQUIREMENTS.get(output_fmt, [])
    if fmt_caps:
        matched = [c for c in fmt_caps if c in capabilities]
        if matched:
            score   += 0.5 * (len(matched) / len(fmt_caps))
            weight_sum += 0.5
            reasons.append(f"✓ format: {', '.join(matched)}")
        else:
            reasons.append(f"✗ format: need one of {fmt_caps}")
            return 0.05, reasons
    else:
        score += 0.5
        weight_sum += 0.5

    # Check preferred projection capabilities (soft, weighted 0.3)
    pref_caps = PROJECTION_PREFERRED_CAPS.get(proj_type, [])
    if pref_caps:
        matched_pref = [c for c in pref_caps if c in capabilities]
        ratio = len(matched_pref) / len(pref_caps)
        score     += 0.3 * ratio
        weight_sum += 0.3
        if matched_pref:
            reasons.append(f"✓ preferred: {', '.join(matched_pref)}")
        else:
            reasons.append(f"→ preferred caps not present (ok)")
    else:
        score += 0.3
        weight_sum += 0.3

    # GPU bonus (weighted 0.2)
    output_spec = task.get("output_spec") or {}
    if "gpu" in (output_spec.get("notes") or "").lower():
        if has_gpu:
            score     += 0.2
            weight_sum += 0.2
            reasons.append("✓ GPU available for GPU-accelerated task")
        else:
            score     += 0.05
            weight_sum += 0.2
            reasons.append("→ GPU not present (will be slower)")
    else:
        score     += 0.2
        weight_sum += 0.2

    final = score / weight_sum if weight_sum > 0 else 0.0
    return round(min(1.0, final), 3), reasons


def score_task(
    task:            dict,
    capabilities:    list[str],
    interest_vector: dict[str, float],
    ram_gb:          float,
    cpu_cores:       int,
    has_gpu:         bool,
    affinity_fn:     Any = None,  # callable(task, interest_vector, caps) → float
) -> TaskScore:
    """
    Compute the composite score for one task on this node.
    """
    from agent.corpus_inspector import task_affinity as _default_affinity

    affinity_fn = affinity_fn or _default_affinity

    cap_score, reasons = capability_match(task, capabilities, ram_gb, cpu_cores, has_gpu)
    sem_score  = affinity_fn(task, interest_vector, capabilities)
    scarcity   = float(task.get("scarcity", 1.0))
    asm_weight = float(task.get("assembly_weight", 1.0))
    bounty     = float(task.get("current_bounty", 0.0))

    total = cap_score * sem_score * scarcity * asm_weight

    return TaskScore(
        task_id           = task["id"],
        label             = task.get("label", ""),
        projection_type   = task.get("projection_type", ""),
        capability_match  = cap_score,
        semantic_affinity = round(sem_score, 3),
        scarcity          = round(scarcity, 3),
        assembly_weight   = round(asm_weight, 3),
        total             = round(total, 4),
        bounty            = bounty,
        reasons           = reasons,
    )


def rank_tasks(
    tasks:           list[dict],
    capabilities:    list[str],
    interest_vector: dict[str, float],
    ram_gb:          float,
    cpu_cores:       int,
    has_gpu:         bool,
    top_k:           int = 10,
    min_cap_score:   float = 0.1,
) -> list[TaskScore]:
    """
    Score and rank a list of tasks for this node.
    Filters out tasks with capability_match below min_cap_score.
    """
    scored = []
    for task in tasks:
        ts = score_task(task, capabilities, interest_vector, ram_gb, cpu_cores, has_gpu)
        if ts.capability_match >= min_cap_score:
            scored.append(ts)

    return sorted(scored, key=lambda s: -s.total)[:top_k]


def format_ranked_list(ranked: list[TaskScore], show_reasons: bool = False) -> str:
    """Format ranked task list for terminal display."""
    lines = []
    for i, ts in enumerate(ranked, start=1):
        bar_total = "█" * int(ts.total * 20)
        lines.append(
            f"  {i:2d}.  [{ts.projection_type[:18]:18s}]  {ts.label[:45]:45s}"
        )
        lines.append(
            f"       score {bar_total:<20s} {ts.total:.3f}"
            f"  ·  bounty {ts.bounty:.0f}pts"
            f"  ·  scarcity {ts.scarcity:.2f}"
        )
        if show_reasons:
            for r in ts.reasons:
                lines.append(f"       {r}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    # Smoke test with dummy data
    import sys
    from agent.corpus_inspector import inspect

    dummy_tasks = [
        {"id": "t1", "label": "Constraint graph diagram", "projection_type": "diagrammatic_structure",
         "output_spec": {"format": "diagram_animation"}, "difficulty": "standard",
         "scarcity": 0.9, "assembly_weight": 1.8, "current_bounty": 145.0},
        {"id": "t2", "label": "Narrate scene 3", "projection_type": "narrative_film",
         "output_spec": {"format": "voiceover"}, "difficulty": "simple",
         "scarcity": 0.5, "assembly_weight": 1.0, "current_bounty": 45.0},
        {"id": "t3", "label": "Logical skeleton summary", "projection_type": "structural_summary",
         "output_spec": {"format": "diagram"}, "difficulty": "complex",
         "scarcity": 1.0, "assembly_weight": 2.0, "current_bounty": 180.0},
    ]

    caps = ["diagram_generation", "mathematical_diagram", "video_rendering_cpu", "standard_compute"]
    iv   = {"mathematics": 0.4, "programming": 0.3, "philosophy": 0.2, "writing": 0.1}

    ranked = rank_tasks(dummy_tasks, caps, iv, ram_gb=16, cpu_cores=8, has_gpu=False)
    print(format_ranked_list(ranked, show_reasons=True))
