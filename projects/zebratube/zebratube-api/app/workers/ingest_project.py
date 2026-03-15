"""
workers/ingest_project.py — import zebra-core artifacts into database

Called after `zebra crawl + zebra project + zebra scripts` completes.
Reads the script manifest and dependency graph, creates a ProjectVersion,
upserts Task rows, inserts TaskDependency rows, and computes initial bounties.

Usage (standalone):
    python3 -m app.workers.ingest_project \\
        --project-slug my-repo \\
        --scripts-dir  /path/to/data/scripts/my-repo \\
        --graph-path   /path/to/data/canonical/my-repo/graph.json \\
        --model        granite4 \\
        --source-commit abc1234

Usage (from FastAPI background task):
    from app.workers.ingest_project import ingest_project
    ingest_project(project_id, scripts_dir, graph_path, ...)
"""

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as script from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db import get_db_session
from app.models.schema import (
    Project, ProjectVersion, Task, TaskDependency,
    TaskDifficulty, TaskStatus, OutputFormat,
)
from app.services.bounty import compute_bounty


# ── helpers ───────────────────────────────────────────────────────────────────

def _difficulty(s: str) -> TaskDifficulty:
    return {
        "simple":   TaskDifficulty.simple,
        "standard": TaskDifficulty.standard,
        "complex":  TaskDifficulty.complex,
    }.get(s, TaskDifficulty.standard)


def _output_format(s: str) -> OutputFormat:
    mapping = {
        "video":             OutputFormat.video,
        "audio":             OutputFormat.audio,
        "animation":         OutputFormat.animation,
        "diagram_animation": OutputFormat.diagram_animation,
        "diagram":           OutputFormat.diagram,
        "screencast":        OutputFormat.screencast,
        "screencast_or_animation": OutputFormat.screencast,
        "voiceover":         OutputFormat.voiceover,
        "voiceover_or_video": OutputFormat.voiceover,
        "audio_or_video":    OutputFormat.audio,
    }
    return mapping.get(s, OutputFormat.video)


def _prompt_hash(prompts_dir: Path) -> str | None:
    p = prompts_dir / "canonical_extract.txt"
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


# ── core function ─────────────────────────────────────────────────────────────

def ingest_project(
    project_id:    str,
    scripts_dir:   str | Path,
    graph_path:    str | Path,
    model:         str = "granite4",
    source_commit: str | None = None,
    prompts_dir:   str | Path | None = None,
) -> str:
    """
    Create a new ProjectVersion and import all tasks from a scripts manifest.
    Returns the new project_version.id.
    """

    scripts_dir = Path(scripts_dir)
    graph_path  = Path(graph_path)
    manifest_path = scripts_dir / "manifest.json"
    deps_path     = scripts_dir / "deps.json"

    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {scripts_dir}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    deps_data = json.loads(deps_path.read_text(encoding="utf-8")) if deps_path.exists() else {}

    # Load corpus stats from graph
    corpus_stats = None
    if graph_path.exists():
        g = json.loads(graph_path.read_text(encoding="utf-8"))
        corpus_stats = g.get("stats") or {
            k: len(g.get(k, [])) for k in
            ["entities", "events", "claims", "ambiguities", "themes", "timeline"]
        }
        corpus_stats["source_documents"] = g.get("stats", {}).get("source_documents", 0)

    prompt_hash = _prompt_hash(Path(prompts_dir)) if prompts_dir else None

    db = get_db_session()
    try:
        # Create ProjectVersion
        # Get next version number
        from sqlalchemy import func as sqlfunc
        max_ver = db.query(sqlfunc.max(ProjectVersion.version_number))\
                    .filter(ProjectVersion.project_id == project_id).scalar() or 0

        version = ProjectVersion(
            project_id             = project_id,
            version_number         = max_ver + 1,
            crawl_timestamp        = datetime.now(timezone.utc),
            source_commit          = source_commit,
            graph_path             = str(graph_path),
            scripts_dir            = str(scripts_dir),
            corpus_stats           = corpus_stats,
            extraction_prompt_hash = prompt_hash,
            model_name             = model,
            is_active              = True,
        )
        db.add(version)
        db.flush()  # get version.id before inserting tasks

        # Deactivate previous versions
        db.query(ProjectVersion)\
          .filter(
              ProjectVersion.project_id == project_id,
              ProjectVersion.id != version.id,
          )\
          .update({"is_active": False})

        tasks_data = manifest.get("tasks", [])
        task_ids_imported: set[str] = set()

        for t in tasks_data:
            tid = t["id"]

            # Compute initial bounty
            bc = compute_bounty(
                base_value=100,
                submission_count=0,
                assembly_weight=t.get("assembly_weight", 1.0),
                is_first=False,
            )

            # Determine bundle path
            bundle_path = str(scripts_dir / f"{tid}.zip")
            if not Path(bundle_path).exists():
                bundle_path = None

            # Upsert: if task with same content-addressed id exists, skip
            existing = db.query(Task).filter(Task.id == tid).first()
            if existing:
                # Update version reference and bounty only
                existing.project_version_id = version.id
                existing.current_bounty     = bc.bounty
                existing.scarcity           = bc.scarcity
            else:
                task = Task(
                    id                  = tid,
                    project_version_id  = version.id,
                    projection_type     = t.get("projection_type", ""),
                    label               = t.get("label", "")[:255],
                    difficulty          = _difficulty(t.get("difficulty", "standard")),
                    output_format       = _output_format(
                        (t.get("output_spec") or {}).get("format", "video")
                    ),
                    duration_estimate_s = t.get("duration_estimate_s"),
                    assembly_weight     = t.get("assembly_weight", 1.0),
                    script_path         = str(scripts_dir / tid),
                    bundle_path         = bundle_path,
                    graph_nodes         = t.get("graph_nodes", []),
                    style_hint          = t.get("style_hint"),
                    output_spec         = t.get("output_spec"),
                    status              = TaskStatus.open,
                    submission_count    = 0,
                    accepted_count      = 0,
                    base_value          = 100,
                    scarcity            = bc.scarcity,
                    current_bounty      = bc.bounty,
                )
                db.add(task)

            task_ids_imported.add(tid)

        db.flush()

        # Import task dependencies
        for dep in deps_data.get("dependencies", []):
            from_id, to_id = dep["from"], dep["to"]
            if from_id not in task_ids_imported or to_id not in task_ids_imported:
                continue
            existing_dep = db.query(TaskDependency)\
                             .filter_by(from_task_id=from_id, to_task_id=to_id)\
                             .first()
            if not existing_dep:
                db.add(TaskDependency(
                    from_task_id = from_id,
                    to_task_id   = to_id,
                    via          = dep.get("via"),
                ))

        db.commit()
        print(f"Ingested {len(task_ids_imported)} tasks into version {version.version_number}")
        return version.id

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── create-project helper ─────────────────────────────────────────────────────

def ensure_project(slug: str, title: str | None = None) -> str:
    """Get or create a project by slug. Returns project.id."""
    db = get_db_session()
    try:
        p = db.query(Project).filter_by(slug=slug).first()
        if p:
            return p.id
        p = Project(
            slug=slug,
            title=title or slug.replace("-", " ").replace("_", " ").title(),
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return p.id
    finally:
        db.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Import zebra-core script artifacts into database")
    ap.add_argument("--project-slug",  required=True)
    ap.add_argument("--scripts-dir",   required=True)
    ap.add_argument("--graph-path",    required=True)
    ap.add_argument("--model",         default="granite4")
    ap.add_argument("--source-commit", default=None)
    ap.add_argument("--title",         default=None)
    ap.add_argument("--prompts-dir",   default=None)
    args = ap.parse_args()

    project_id = ensure_project(args.project_slug, args.title)
    print(f"Project: {args.project_slug} ({project_id})")

    version_id = ingest_project(
        project_id    = project_id,
        scripts_dir   = args.scripts_dir,
        graph_path    = args.graph_path,
        model         = args.model,
        source_commit = args.source_commit,
        prompts_dir   = args.prompts_dir,
    )
    print(f"Version created: {version_id}")


if __name__ == "__main__":
    main()
