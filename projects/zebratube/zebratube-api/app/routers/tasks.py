"""
routers/tasks.py — task browsing, filtering, bundle download, and live bounty
"""
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db import get_db
from app.models.schema import Task, TaskDependency, Submission, ProjectVersion
from app.services.bounty import compute_bounty

router = APIRouter()

class TaskOut(BaseModel):
    id: str
    project_version_id: str
    projection_type: str
    label: str
    difficulty: str
    output_format: str
    duration_estimate_s: Optional[int]
    assembly_weight: float
    status: str
    submission_count: int
    accepted_count: int
    current_bounty: float
    scarcity: float
    style_hint: Optional[str]
    output_spec: Optional[dict]
    graph_nodes: Optional[list]
    depends_on: Optional[list]
    created_at: datetime
    class Config: from_attributes = True

def _out(t: Task) -> dict:
    deps = [d.from_task_id for d in (t.incoming_deps or [])]
    return TaskOut(
        id=t.id, project_version_id=t.project_version_id,
        projection_type=t.projection_type, label=t.label,
        difficulty=t.difficulty.value, output_format=t.output_format.value,
        duration_estimate_s=t.duration_estimate_s, assembly_weight=t.assembly_weight,
        status=t.status.value, submission_count=t.submission_count,
        accepted_count=t.accepted_count, current_bounty=t.current_bounty,
        scarcity=t.scarcity, style_hint=t.style_hint, output_spec=t.output_spec,
        graph_nodes=t.graph_nodes, depends_on=deps, created_at=t.created_at,
    )

def _media_url(path: Optional[str]) -> Optional[str]:
    if not path: return None
    root = os.environ.get("MEDIA_ROOT", "/tmp/zebratube/media")
    return f"/media/{path[len(root):].lstrip('/')}" if path.startswith(root) else path

@router.get("/", response_model=list[TaskOut])
def list_tasks(
    project_id: Optional[str]=None, projection_type: Optional[str]=None,
    difficulty: Optional[str]=None, status: str=Query(default="open"),
    min_bounty: Optional[float]=None,
    sort_by: str=Query(default="bounty", enum=["bounty","scarcity","weight","created"]),
    limit: int=Query(default=20,le=100), offset: int=0,
    db: Session=Depends(get_db),
):
    q = db.query(Task)
    if project_id:
        q = q.join(ProjectVersion).filter(ProjectVersion.project_id==project_id)
    if projection_type: q = q.filter(Task.projection_type==projection_type)
    if difficulty: q = q.filter(Task.difficulty==difficulty)
    if status and status!="all": q = q.filter(Task.status==status)
    if min_bounty is not None: q = q.filter(Task.current_bounty>=min_bounty)
    col = {"bounty":desc(Task.current_bounty),"scarcity":desc(Task.scarcity),
           "weight":desc(Task.assembly_weight),"created":desc(Task.created_at)}.get(sort_by,desc(Task.current_bounty))
    return [_out(t) for t in q.order_by(col).offset(offset).limit(limit).all()]

@router.get("/bottlenecks", response_model=list[TaskOut])
def bottleneck_tasks(limit: int=Query(default=10,le=20), db: Session=Depends(get_db)):
    """High-centrality tasks with zero submissions."""
    tasks = db.query(Task).filter(Task.status=="open", Task.submission_count==0)              .order_by(desc(Task.assembly_weight), desc(Task.current_bounty))              .limit(limit).all()
    return [_out(t) for t in tasks]

@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session=Depends(get_db)):
    t = db.query(Task).filter(Task.id==task_id).first()
    if not t: raise HTTPException(404, f"task not found: {task_id}")
    return _out(t)

@router.get("/{task_id}/bundle")
def download_bundle(task_id: str, db: Session=Depends(get_db)):
    t = db.query(Task).filter(Task.id==task_id).first()
    if not t: raise HTTPException(404,"task not found")
    if not t.bundle_path or not os.path.exists(t.bundle_path):
        raise HTTPException(404,"bundle not generated yet")
    return FileResponse(t.bundle_path, media_type="application/zip",
                        filename=f"task_{task_id}.zip")

@router.get("/{task_id}/submissions")
def task_submissions(task_id: str, db: Session=Depends(get_db)):
    t = db.query(Task).filter(Task.id==task_id).first()
    if not t: raise HTTPException(404,"task not found")
    subs = db.query(Submission).filter(Submission.task_id==task_id)             .order_by(Submission.submitted_at).all()
    return [{"id":s.id,"task_id":s.task_id,"user_id":s.user_id,
             "claim_id":s.claim_id,"status":s.status.value,
             "branch_label":s.branch_label,"preview_url":_media_url(s.preview_path),
             "thumbnail_url":_media_url(s.thumbnail_path),
             "media_metadata":s.media_metadata,"notes":s.notes,
             "submitted_at":s.submitted_at.isoformat()} for s in subs]

@router.get("/{task_id}/bounty")
def task_bounty(task_id: str, db: Session=Depends(get_db)):
    t = db.query(Task).filter(Task.id==task_id).first()
    if not t: raise HTTPException(404,"task not found")
    bc = compute_bounty(t.base_value, t.submission_count, t.assembly_weight)
    return {"task_id":task_id,"bounty":bc.bounty,"scarcity":bc.scarcity,
            "assembly_weight":bc.assembly_weight,"submission_count":bc.submission_count,
            "breakdown":bc.breakdown}
