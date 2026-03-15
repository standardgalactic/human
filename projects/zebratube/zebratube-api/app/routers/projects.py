"""
routers/projects.py — project and project version CRUD
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db import get_db
from app.models.schema import Project, ProjectVersion

router = APIRouter()

class ProjectCreate(BaseModel):
    slug: str
    title: str
    description: Optional[str]=None
    project_type: str="mixed"
    source_url: Optional[str]=None
    is_public: bool=True

class ProjectVersionIngest(BaseModel):
    source_path: Optional[str]=None
    source_url: Optional[str]=None
    source_commit: Optional[str]=None
    model: str="granite4"
    title_override: Optional[str]=None

def _proj_out(p: Project) -> dict:
    versions = p.versions or []
    active = next((v for v in reversed(versions) if v.is_active), None)
    return {
        "id": p.id, "slug": p.slug, "title": p.title,
        "description": p.description, "project_type": p.project_type.value,
        "source_url": p.source_url, "is_public": p.is_public,
        "created_at": p.created_at.isoformat(),
        "version_count": len(versions),
        "latest_version_id": active.id if active else None,
        "corpus_stats": active.corpus_stats if active else None,
    }

def _ver_out(v: ProjectVersion) -> dict:
    return {
        "id": v.id, "project_id": v.project_id,
        "version_number": v.version_number,
        "crawl_timestamp": v.crawl_timestamp.isoformat(),
        "source_commit": v.source_commit, "model_name": v.model_name,
        "corpus_stats": v.corpus_stats,
        "task_count": len(v.tasks) if v.tasks else 0,
        "is_active": v.is_active,
    }

@router.get("/")
def list_projects(project_type: Optional[str]=None,
    limit: int=Query(default=20,le=100), offset: int=0,
    db: Session=Depends(get_db)):
    q = db.query(Project).filter(Project.is_public==True)
    if project_type: q = q.filter(Project.project_type==project_type)
    return [_proj_out(p) for p in q.order_by(desc(Project.created_at)).offset(offset).limit(limit).all()]

@router.post("/", status_code=201)
def create_project(body: ProjectCreate, db: Session=Depends(get_db)):
    if db.query(Project).filter(Project.slug==body.slug).first():
        raise HTTPException(409, f"slug already exists: {body.slug}")
    p = Project(id=str(uuid.uuid4()), slug=body.slug, title=body.title,
                description=body.description, project_type=body.project_type,
                source_url=body.source_url, is_public=body.is_public)
    db.add(p); db.commit(); db.refresh(p)
    return _proj_out(p)

@router.get("/{slug}")
def get_project(slug: str, db: Session=Depends(get_db)):
    p = db.query(Project).filter(Project.slug==slug).first()
    if not p: raise HTTPException(404, f"project not found: {slug}")
    return _proj_out(p)

@router.get("/{slug}/versions")
def list_versions(slug: str, db: Session=Depends(get_db)):
    p = db.query(Project).filter(Project.slug==slug).first()
    if not p: raise HTTPException(404, f"project not found: {slug}")
    return [_ver_out(v) for v in p.versions]

@router.post("/{slug}/ingest", status_code=202)
def ingest_version(slug: str, body: ProjectVersionIngest,
    background_tasks: BackgroundTasks, db: Session=Depends(get_db)):
    p = db.query(Project).filter(Project.slug==slug).first()
    if not p: raise HTTPException(404, f"project not found: {slug}")
    # Background: run zebra crawl + extract + scripts, then call ingest worker
    return {"status": "queued", "project_slug": slug, "project_id": p.id}

@router.get("/{slug}/versions/{version_id}/graph")
def get_graph(slug: str, version_id: str, db: Session=Depends(get_db)):
    import json, pathlib
    v = db.query(ProjectVersion).filter(ProjectVersion.id==version_id).first()
    if not v: raise HTTPException(404,"version not found")
    if not v.graph_path or not pathlib.Path(v.graph_path).exists():
        raise HTTPException(404,"graph file not found on disk")
    return json.loads(pathlib.Path(v.graph_path).read_text())

@router.get("/{slug}/wiki")
def get_wiki(slug: str, style: str="science", db: Session=Depends(get_db)):
    import json, pathlib
    p = db.query(Project).filter(Project.slug==slug).first()
    if not p: raise HTTPException(404,"project not found")
    active = next((v for v in reversed(p.versions or []) if v.is_active), None)
    if not active or not active.wiki_dir:
        raise HTTPException(404,"wiki not generated yet")
    # Find article for first theme in the requested style
    wiki_path = pathlib.Path(active.wiki_dir)
    for theme_dir in sorted(wiki_path.glob("articles/*/")): 
        art = theme_dir / f"{style}.json"
        if art.exists():
            return json.loads(art.read_text())
    raise HTTPException(404, f"no {style} article found")
