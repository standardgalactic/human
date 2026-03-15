"""
app/workers/ingest.py — import zebra-core artifacts into the database.

Called after `zebra crawl` and `zebra scripts` have run.
Reads manifest.json, corpus_graph.json, and scripts/manifest.json,
then populates project_versions, tasks, task_dependencies.

Usage (standalone):
    python -m app.workers.ingest \
        --project-slug my-project \
        --zebra-dir    /path/to/zebra-core/data \
        --stem         my_repo

Or called via Celery task: ingest_project.delay(project_slug, stem, zebra_dir)
"""

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Bounty computation (inline, no circular import) ──────────────────────────

def compute_bounty(base: int, sub_count: int, weight: float) -> float:
    scarcity = 1.0 / (1.0 + sub_count)
    return round(base * math.log1p(scarcity) * weight, 1)


# ── Main ingestion logic ──────────────────────────────────────────────────────

def ingest(
    project_slug:  str,
    stem:          str,
    zebra_dir:     str,
    model_name:    str = "granite4",
    db_session=None,    # SQLAlchemy Session; None = dry-run mode
) -> dict:
    """
    Import all zebra-core artifacts for one project version into the database.
    Returns a summary dict.
    """
    base = Path(zebra_dir)

    # Paths
    corpus_graph_path = base / "wiki"    / stem / "corpus_graph.json"
    canon_graph_path  = base / "canonical" / stem / "graph.json"
    scripts_manifest  = base / "scripts" / stem / "manifest.json"
    wiki_dir          = base / "wiki"    / stem
    scripts_dir       = base / "scripts" / stem

    # Prefer corpus graph over single-doc graph
    graph_path = corpus_graph_path if corpus_graph_path.exists() else canon_graph_path

    if not graph_path.exists():
        raise FileNotFoundError(f"No graph found for stem '{stem}' in {zebra_dir}")

    graph = json.loads(graph_path.read_text(encoding="utf-8"))

    # Corpus stats
    stats = graph.get("stats") or {
        "entities":         len(graph.get("entities", [])),
        "events":           len(graph.get("events",   [])),
        "claims":           len(graph.get("claims",   [])),
        "ambiguities":      len(graph.get("ambiguities", [])),
        "themes":           len(graph.get("themes",   [])),
        "source_documents": graph.get("stats", {}).get("source_documents", 0),
    }

    # Extraction prompt hash (content-address the prompt for auditability)
    prompt_path = Path(zebra_dir).parent / "prompts" / "canonical_extract.txt"
    prompt_hash = ""
    if prompt_path.exists():
        prompt_hash = hashlib.sha256(prompt_path.read_bytes()).hexdigest()[:16]

    version_record = {
        "project_slug":           project_slug,
        "stem":                   stem,
        "crawl_timestamp":        datetime.now(timezone.utc).isoformat(),
        "graph_path":             str(graph_path),
        "wiki_dir":               str(wiki_dir) if wiki_dir.exists() else None,
        "scripts_dir":            str(scripts_dir) if scripts_dir.exists() else None,
        "corpus_stats":           stats,
        "extraction_prompt_hash": prompt_hash,
        "model_name":             model_name,
    }

    # Load task scripts
    task_records = []
    dep_records  = []

    if scripts_manifest.exists():
        manifest = json.loads(scripts_manifest.read_text(encoding="utf-8"))
        tasks = manifest.get("tasks", [])

        for t in tasks:
            bundle_path = scripts_dir / f"{t['id']}.zip"
            task_records.append({
                "id":                   t["id"],
                "projection_type":      t["projection_type"],
                "label":                t["label"],
                "difficulty":           t.get("difficulty", "standard"),
                "output_format":        t.get("output_spec", {}).get("format", "video"),
                "duration_estimate_s":  t.get("duration_estimate_s"),
                "assembly_weight":      t.get("assembly_weight", 1.0),
                "script_path":          str(scripts_dir / t["id"]),
                "bundle_path":          str(bundle_path) if bundle_path.exists() else None,
                "graph_nodes":          t.get("graph_nodes", []),
                "style_hint":           t.get("style_hint"),
                "output_spec":          t.get("output_spec"),
                "base_value":           100,
                "scarcity":             1.0,
                "current_bounty":       compute_bounty(100, 0, t.get("assembly_weight", 1.0)),
            })

        # Load dependency graph
        deps_path = scripts_dir / "deps.json"
        if deps_path.exists():
            deps_data = json.loads(deps_path.read_text(encoding="utf-8"))
            for d in deps_data.get("dependencies", []):
                dep_records.append({
                    "from_task_id": d["from"],
                    "to_task_id":   d["to"],
                    "via":          d.get("via"),
                })

    summary = {
        "project_slug":  project_slug,
        "stem":          stem,
        "version":       version_record,
        "task_count":    len(task_records),
        "dep_count":     len(dep_records),
        "corpus_stats":  stats,
        "dry_run":       db_session is None,
    }

    if db_session is not None:
        _write_to_db(db_session, project_slug, version_record, task_records, dep_records)
        summary["written"] = True
    else:
        print("[dry-run] would write:")
        print(f"  version:      {json.dumps(version_record, indent=2, default=str)}")
        print(f"  tasks:        {len(task_records)}")
        print(f"  dependencies: {len(dep_records)}")

    return summary


def _write_to_db(session, project_slug, version_record, task_records, dep_records):
    """Write ingestion data to PostgreSQL via SQLAlchemy."""
    from app.models.schema import Project, ProjectVersion, Task, TaskDependency
    from sqlalchemy import select

    # Find or create project
    project = session.execute(
        select(Project).where(Project.slug == project_slug)
    ).scalar_one_or_none()

    if not project:
        project = Project(
            slug=project_slug,
            title=project_slug.replace("_", " ").title(),
        )
        session.add(project)
        session.flush()

    # Determine next version number
    latest = session.execute(
        select(ProjectVersion.version_number)
        .where(ProjectVersion.project_id == project.id)
        .order_by(ProjectVersion.version_number.desc())
        .limit(1)
    ).scalar()
    next_version = (latest or 0) + 1

    # Deactivate previous active versions
    session.execute(
        ProjectVersion.__table__.update()
        .where(ProjectVersion.project_id == project.id)
        .values(is_active=False)
    )

    # Create version
    pv = ProjectVersion(
        project_id=             project.id,
        version_number=         next_version,
        crawl_timestamp=        datetime.fromisoformat(version_record["crawl_timestamp"]),
        graph_path=             version_record.get("graph_path"),
        wiki_dir=               version_record.get("wiki_dir"),
        scripts_dir=            version_record.get("scripts_dir"),
        corpus_stats=           version_record.get("corpus_stats"),
        extraction_prompt_hash= version_record.get("extraction_prompt_hash"),
        model_name=             version_record.get("model_name"),
        is_active=              True,
    )
    session.add(pv)
    session.flush()

    # Insert tasks
    for t in task_records:
        task = Task(project_version_id=pv.id, **t)
        session.merge(task)   # merge by primary key (stable id)

    session.flush()

    # Insert dependencies
    for d in dep_records:
        dep = TaskDependency(
            from_task_id=d["from_task_id"],
            to_task_id=  d["to_task_id"],
            via=         d.get("via"),
        )
        try:
            session.merge(dep)
        except Exception:
            pass  # ignore duplicate deps

    session.commit()


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-slug", required=True)
    ap.add_argument("--stem",         required=True)
    ap.add_argument("--zebra-dir",    required=True)
    ap.add_argument("--model",        default="granite4")
    ap.add_argument("--dry-run",      action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        result = ingest(args.project_slug, args.stem, args.zebra_dir,
                        model_name=args.model, db_session=None)
    else:
        from app.db import SessionLocal
        db = SessionLocal()
        try:
            result = ingest(args.project_slug, args.stem, args.zebra_dir,
                            model_name=args.model, db_session=db)
        finally:
            db.close()

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
