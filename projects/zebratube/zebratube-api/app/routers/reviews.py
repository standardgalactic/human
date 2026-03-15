"""
routers/reviews.py — selector verdict submission + point award
"""
import uuid
import math
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.schema import (SubmissionReview, Submission, SubmissionStatus,
    ReviewVerdict, Task, TaskStatus, PointLedger, PointEventType, User)

router = APIRouter()

class ReviewCreate(BaseModel):
    submission_id: str
    verdict: str
    notes: Optional[str]=None

VERDICT_MAP = {
    "approve": ReviewVerdict.approve,
    "reject": ReviewVerdict.reject,
    "request_revision": ReviewVerdict.request_revision,
    "preserve_branch": ReviewVerdict.preserve_branch,
}

def _get_current_user_id(db: Session) -> str:
    u = db.query(User).first()
    if not u: raise HTTPException(401,"not authenticated")
    return u.id

def _award_selector_points(user_id: str, task: Task, db: Session):
    points = max(1, round(task.current_bounty * 0.05))
    u = db.query(User).filter(User.id==user_id).first()
    if not u: return
    u.point_balance += points
    db.add(PointLedger(id=str(uuid.uuid4()), user_id=user_id,
        event_type=PointEventType.selector_comparison, delta=points,
        balance_after=u.point_balance, task_id=task.id,
        description=f"selector comparison on {task.label[:60]}"))

@router.post("/", status_code=201)
def create_review(body: ReviewCreate, db: Session=Depends(get_db)):
    reviewer_id = _get_current_user_id(db)
    sub = db.query(Submission).filter(Submission.id==body.submission_id).first()
    if not sub: raise HTTPException(404,"submission not found")
    # Check not already reviewed by this user
    existing = db.query(SubmissionReview).filter(
        SubmissionReview.submission_id==body.submission_id,
        SubmissionReview.reviewer_id==reviewer_id).first()
    if existing: raise HTTPException(409,"already reviewed this submission")
    verdict = VERDICT_MAP.get(body.verdict)
    if not verdict: raise HTTPException(422, f"unknown verdict: {body.verdict}")
    r = SubmissionReview(id=str(uuid.uuid4()), submission_id=body.submission_id,
        reviewer_id=reviewer_id, verdict=verdict, notes=body.notes,
        reviewed_at=datetime.now(timezone.utc))
    # Apply verdict to submission status
    if verdict == ReviewVerdict.approve:
        sub.status = SubmissionStatus.accepted
        task = db.query(Task).filter(Task.id==sub.task_id).first()
        if task:
            task.accepted_count = (task.accepted_count or 0) + 1
            if task.accepted_count >= 1:
                task.status = TaskStatus.accepted
    elif verdict == ReviewVerdict.reject:
        sub.status = SubmissionStatus.rejected
    elif verdict == ReviewVerdict.preserve_branch:
        sub.status = SubmissionStatus.branch
    # Award selector points
    task = db.query(Task).filter(Task.id==sub.task_id).first()
    if task: _award_selector_points(reviewer_id, task, db)
    db.add(r); db.commit()
    return {"id":r.id,"submission_id":r.submission_id,"reviewer_id":r.reviewer_id,
            "verdict":r.verdict.value,"notes":r.notes,
            "reviewed_at":r.reviewed_at.isoformat()}

@router.get("/submission/{submission_id}")
def reviews_for_submission(submission_id: str, db: Session=Depends(get_db)):
    rs = db.query(SubmissionReview).filter(
        SubmissionReview.submission_id==submission_id).all()
    return [{"id":r.id,"submission_id":r.submission_id,"reviewer_id":r.reviewer_id,
             "verdict":r.verdict.value,"notes":r.notes,
             "reviewed_at":r.reviewed_at.isoformat()} for r in rs]
