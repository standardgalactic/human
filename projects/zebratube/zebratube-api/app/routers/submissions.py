"""
routers/submissions.py — upload, transcode, and retrieve submissions
"""
import hashlib
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.schema import (Submission, SubmissionStatus, Claim, ClaimStatus,
    Task, User, PointLedger, PointEventType)
from app.workers.transcode_worker import transcode_submission

router = APIRouter()

MEDIA_ROOT   = os.environ.get("MEDIA_ROOT", "/tmp/zebratube/media")
UPLOAD_DIR   = os.path.join(MEDIA_ROOT, "uploads")
ACCEPTED_TYPES = {
    "video/mp4","video/webm","video/quicktime","video/x-msvideo",
    "audio/mpeg","audio/wav","audio/ogg","audio/mp4",
    "image/png","image/svg+xml","image/jpeg","image/gif",
}

def _get_current_user_id(db: Session) -> str:
    u = db.query(User).first()
    if not u: raise HTTPException(401,"not authenticated")
    return u.id

def _sub_out(s: Submission) -> dict:
    root = os.environ.get("MEDIA_ROOT","/tmp/zebratube/media")
    def url(p):
        if not p: return None
        return f"/media/{p[len(root):].lstrip('/')}" if p.startswith(root) else p
    return {"id":s.id,"task_id":s.task_id,"user_id":s.user_id,"claim_id":s.claim_id,
            "status":s.status.value,"branch_label":s.branch_label,
            "preview_url":url(s.preview_path),"thumbnail_url":url(s.thumbnail_path),
            "media_metadata":s.media_metadata,"notes":s.notes,
            "submitted_at":s.submitted_at.isoformat()}

@router.post("/", status_code=201)
async def upload_submission(
    background_tasks: BackgroundTasks,
    claim_id: str=Form(...), task_id: str=Form(...),
    branch_label: Optional[str]=Form(default=None),
    notes: Optional[str]=Form(default=None),
    file: UploadFile=File(...),
    db: Session=Depends(get_db),
):
    user_id = _get_current_user_id(db)
    if file.content_type not in ACCEPTED_TYPES:
        raise HTTPException(415, f"unsupported media type: {file.content_type}")
    # Validate claim
    claim = db.query(Claim).filter(Claim.id==claim_id, Claim.user_id==user_id,
        Claim.status==ClaimStatus.active).first()
    if not claim: raise HTTPException(403,"no active claim found")
    task = db.query(Task).filter(Task.id==task_id).first()
    if not task: raise HTTPException(404,"task not found")
    # Save file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    sub_id = str(uuid.uuid4())
    dest = os.path.join(UPLOAD_DIR, f"{sub_id}{ext}")
    contents = await file.read()
    file_hash = hashlib.sha256(contents).hexdigest()
    with open(dest,"wb") as f: f.write(contents)
    # Create submission record
    sub = Submission(id=sub_id, claim_id=claim_id, task_id=task_id,
        user_id=user_id, status=SubmissionStatus.pending,
        branch_label=branch_label, notes=notes,
        original_path=dest, file_hash=file_hash,
        submitted_at=datetime.now(timezone.utc))
    task.submission_count = (task.submission_count or 0) + 1
    # Recalculate scarcity
    from app.services.bounty import compute_bounty
    bc = compute_bounty(task.base_value, task.submission_count, task.assembly_weight)
    task.scarcity = bc.scarcity; task.current_bounty = bc.bounty
    db.add(sub); db.commit(); db.refresh(sub)
    # Enqueue transcode
    background_tasks.add_task(transcode_submission, sub_id, dest)
    return _sub_out(sub)

@router.get("/{submission_id}")
def get_submission(submission_id: str, db: Session=Depends(get_db)):
    s = db.query(Submission).filter(Submission.id==submission_id).first()
    if not s: raise HTTPException(404,"submission not found")
    return _sub_out(s)

@router.get("/task/{task_id}")
def submissions_for_task(task_id: str, db: Session=Depends(get_db)):
    subs = db.query(Submission).filter(Submission.task_id==task_id)             .order_by(Submission.submitted_at).all()
    return [_sub_out(s) for s in subs]
