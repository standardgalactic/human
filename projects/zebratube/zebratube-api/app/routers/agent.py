"""
routers/agent.py — agent registration and capability-filtered task dispatch

Nodes register their capability profiles here.
The /register endpoint stores profiles in-memory (or DB) for analytics.
The /tasks endpoint returns capability-filtered, scored task recommendations.
"""

import socket
import time
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db import get_db
from app.models.schema import Task, ProjectVersion

router = APIRouter()

# ── In-memory node registry (replace with DB table for production) ────────────
_node_registry: dict[str, dict] = {}


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class HardwareProfile(BaseModel):
    cpu_cores:     int
    ram_gb:        float
    disk_free_gb:  float
    has_gpu:       bool
    gpu_names:     list[str] = []
    total_vram_gb: float = 0.0
    gpu_backend:   str = "none"
    has_mic:       bool = False
    has_camera:    bool = False
    has_display:   bool = False
    platform:      str = "unknown"
    capabilities:  list[str] = []
    tools:         dict[str, bool] = {}


class NodeRegistration(BaseModel):
    node_name:    Optional[str] = None
    capabilities: HardwareProfile
    interest_vector: Optional[dict[str, float]] = None


class NodeRegistrationOut(BaseModel):
    node_id:       str
    registered_at: str
    task_count:    int


# ── Capability → output format compatibility ──────────────────────────────────

FORMAT_COMPATIBLE_CAPS: dict[str, set[str]] = {
    "video":             {"video_rendering_cpu", "video_rendering_gpu",
                         "screen_recording", "3d_animation"},
    "animation":         {"3d_animation", "diagram_generation", "video_rendering_cpu"},
    "diagram_animation": {"diagram_generation", "video_rendering_cpu"},
    "diagram":           {"diagram_generation", "vector_graphics", "mathematical_diagram"},
    "audio":             {"narration", "audio_processing"},
    "voiceover":         {"narration"},
    "screencast":        {"screen_recording"},
    "screencast_or_animation": {"screen_recording", "diagram_generation"},
    "voiceover_or_video":      {"narration", "video_rendering_cpu"},
    "audio_or_video":          {"narration", "video_rendering_cpu", "audio_processing"},
}

DIFFICULTY_RAM: dict[str, float] = {
    "simple":   4.0,
    "standard": 8.0,
    "complex":  16.0,
}


def _node_can_do(task: Task, hw: HardwareProfile) -> bool:
    """Quick server-side pre-filter: can this node physically execute the task?"""
    difficulty = task.difficulty.value if hasattr(task.difficulty, 'value') else str(task.difficulty)
    min_ram = DIFFICULTY_RAM.get(difficulty, 8.0)
    if hw.ram_gb < min_ram:
        return False

    output_fmt = (task.output_spec or {}).get("format", "video")
    required   = FORMAT_COMPATIBLE_CAPS.get(output_fmt, set())
    if required and not required.intersection(set(hw.capabilities)):
        return False

    return True


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=NodeRegistrationOut)
def register_node(body: NodeRegistration, db: Session = Depends(get_db)):
    """
    Register or update a node's capability profile.
    Returns the count of tasks currently matching this node.
    """
    from datetime import datetime, timezone
    node_id  = body.node_name or socket.gethostname()
    now      = datetime.now(timezone.utc).isoformat()

    _node_registry[node_id] = {
        "registered_at":    now,
        "capabilities":     body.capabilities.model_dump(),
        "interest_vector":  body.interest_vector or {},
    }

    # Count matching open tasks for feedback
    tasks = db.query(Task).filter(Task.status == "open").limit(500).all()
    matching = sum(1 for t in tasks if _node_can_do(t, body.capabilities))

    return NodeRegistrationOut(
        node_id=node_id,
        registered_at=now,
        task_count=matching,
    )


@router.get("/tasks")
def agent_tasks(
    capabilities:     str = Query(default="", description="comma-separated capability list"),
    ram_gb:           float = Query(default=8.0),
    has_gpu:          bool  = Query(default=False),
    cpu_cores:        int   = Query(default=4),
    interest_vector:  str = Query(default="", description="JSON-encoded topic weights"),
    limit:            int = Query(default=20, le=50),
    db:               Session = Depends(get_db),
):
    """
    Return open tasks pre-filtered by hardware capabilities.
    The client-side agent performs final ranking; this endpoint
    does a coarse capability match to reduce payload size.
    """
    import json as _json

    cap_set = set(c.strip() for c in capabilities.split(",") if c.strip())
    iv: dict[str, float] = {}
    if interest_vector:
        try:
            iv = _json.loads(interest_vector)
        except Exception:
            pass

    hw = HardwareProfile(
        cpu_cores=cpu_cores,
        ram_gb=ram_gb,
        has_gpu=has_gpu,
        capabilities=list(cap_set),
    )

    tasks = (
        db.query(Task)
        .filter(Task.status == "open")
        .order_by(desc(Task.assembly_weight), desc(Task.scarcity))
        .limit(200)
        .all()
    )

    eligible = [t for t in tasks if _node_can_do(t, hw)]

    # Lightweight topic boost if interest vector provided
    def _topic_boost(task: Task) -> float:
        if not iv:
            return 0.0
        proj  = task.projection_type or ""
        label = (task.label or "").lower()
        from routers.agent import _PROJ_TOPICS
        topics = _PROJ_TOPICS.get(proj, [])
        return sum(iv.get(t, 0.0) for t in topics) * 0.2

    eligible.sort(key=lambda t: -(
        t.assembly_weight * t.scarcity * t.current_bounty + _topic_boost(t) * 100
    ))

    return [
        {
            "id":                  t.id,
            "label":               t.label,
            "projection_type":     t.projection_type,
            "difficulty":          t.difficulty.value,
            "output_format":       t.output_format.value,
            "output_spec":         t.output_spec,
            "duration_estimate_s": t.duration_estimate_s,
            "assembly_weight":     t.assembly_weight,
            "scarcity":            t.scarcity,
            "current_bounty":      t.current_bounty,
            "submission_count":    t.submission_count,
            "status":              t.status.value,
            "graph_nodes":         t.graph_nodes,
            "style_hint":          t.style_hint,
        }
        for t in eligible[:limit]
    ]


# Topic map for lightweight server-side boost
_PROJ_TOPICS: dict[str, list[str]] = {
    "narrative_film":         ["writing", "video_audio"],
    "diagrammatic_structure": ["mathematics", "programming"],
    "ambiguity_diffusion":    ["mathematics", "philosophy"],
    "rhetorical_voice":       ["writing", "philosophy"],
    "sonic_mapping":          ["music", "mathematics"],
    "structural_summary":     ["mathematics", "philosophy"],
    "procedural_transform":   ["programming"],
    "concept_map":            ["programming", "mathematics"],
    "timeline_causality":     ["writing", "programming"],
    "character_state":        ["writing"],
}
