"""
routers/assemblies.py — assembly creation, spec, and render trigger
"""
import json
import uuid
import subprocess
import sys
import os
import tempfile
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.schema import (Assembly, AssemblySegment, Submission,
    Task, ProjectVersion, User)

router = APIRouter()

class SegmentSpec(BaseModel):
    task_id: str
    submission_id: Optional[str]=None
    position: int
    is_canonical: bool=True
    branch_label: Optional[str]=None
    notes: Optional[str]=None

class AssemblyCreate(BaseModel):
    project_version_id: str
    title: Optional[str]=None
    segments: list[SegmentSpec]=[]

def _get_current_user_id(db: Session) -> str:
    u = db.query(User).first()
    if not u: raise HTTPException(401,"not authenticated")
    return u.id

def _asm_out(a: Assembly, db: Session) -> dict:
    segs = a.segments or []
    gaps = sum(1 for s in segs if s.submission_id is None)
    return {"id":a.id,"project_version_id":a.project_version_id,
            "assembler_id":a.assembler_id,"title":a.title,"status":a.status,
            "output_url":a.output_path,"segment_count":len(segs),"gap_count":gaps,
            "created_at":a.created_at.isoformat(),
            "updated_at":a.updated_at.isoformat() if a.updated_at else None}

@router.post("/", status_code=201)
def create_assembly(body: AssemblyCreate, db: Session=Depends(get_db)):
    user_id = _get_current_user_id(db)
    v = db.query(ProjectVersion).filter(ProjectVersion.id==body.project_version_id).first()
    if not v: raise HTTPException(404,"project version not found")
    a = Assembly(id=str(uuid.uuid4()), project_version_id=body.project_version_id,
                 assembler_id=user_id, title=body.title, status="draft",
                 created_at=datetime.now(timezone.utc))
    db.add(a); db.flush()
    for seg in sorted(body.segments, key=lambda s: s.position):
        db.add(AssemblySegment(id=str(uuid.uuid4()), assembly_id=a.id,
            task_id=seg.task_id, submission_id=seg.submission_id,
            position=seg.position, is_canonical=seg.is_canonical,
            branch_label=seg.branch_label, notes=seg.notes))
    db.commit(); db.refresh(a)
    return _asm_out(a, db)

@router.get("/{assembly_id}")
def get_assembly(assembly_id: str, db: Session=Depends(get_db)):
    a = db.query(Assembly).filter(Assembly.id==assembly_id).first()
    if not a: raise HTTPException(404,"assembly not found")
    return _asm_out(a, db)

@router.get("/{assembly_id}/spec")
def get_assembly_spec(assembly_id: str, db: Session=Depends(get_db)):
    a = db.query(Assembly).filter(Assembly.id==assembly_id).first()
    if not a: raise HTTPException(404,"assembly not found")
    segs = sorted(a.segments or [], key=lambda s: s.position)
    return {"assembly_id":a.id,"title":a.title,"segments":[
        {"position":s.position,"task_id":s.task_id,"submission_id":s.submission_id,
         "is_canonical":s.is_canonical,"branch_label":s.branch_label} for s in segs]}

def _render_assembly(assembly_id: str, db_url: str):
    """Background task: ffmpeg concat render."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    a = db.query(Assembly).filter(Assembly.id==assembly_id).first()
    if not a: return
    segs = sorted(a.segments or [], key=lambda s: s.position)
    paths = []
    for seg in segs:
        if not seg.submission_id: continue
        sub = db.query(Submission).filter(Submission.id==seg.submission_id).first()
        if sub and sub.preview_path and os.path.exists(sub.preview_path):
            paths.append(sub.preview_path)
    if not paths: return
    media_root = os.environ.get("MEDIA_ROOT","/tmp/zebratube/media")
    out_dir = os.path.join(media_root,"assemblies"); os.makedirs(out_dir,exist_ok=True)
    out_path = os.path.join(out_dir,f"{assembly_id}.mp4")
    with tempfile.NamedTemporaryFile("w",suffix=".txt",delete=False) as f:
        for p in paths: f.write(f"file '{p}'\n")
        concat_file = f.name
    try:
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat_file,
                        "-c","copy",out_path], timeout=300, check=True, capture_output=True)
        a.output_path = out_path; a.status = "ready"
    except Exception: a.status = "render_failed"
    finally:
        os.unlink(concat_file)
        db.commit(); db.close()

@router.post("/{assembly_id}/render", status_code=202)
def render_assembly(assembly_id: str, background_tasks: BackgroundTasks,
    db: Session=Depends(get_db)):
    a = db.query(Assembly).filter(Assembly.id==assembly_id).first()
    if not a: raise HTTPException(404,"assembly not found")
    a.status = "rendering"; db.commit()
    db_url = os.environ.get("DATABASE_URL","postgresql://zebratube:zebratube@localhost:5432/zebratube")
    background_tasks.add_task(_render_assembly, assembly_id, db_url)
    return {"status":"rendering","assembly_id":assembly_id}
