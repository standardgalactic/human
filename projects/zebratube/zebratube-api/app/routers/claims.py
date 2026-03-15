"""
routers/claims.py — task claiming and withdrawal
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.schema import Claim, Task, ClaimStatus, TaskStatus, User

router = APIRouter()

CLAIM_WINDOW_HOURS = 72

class ClaimCreate(BaseModel):
    task_id: str

def _claim_out(c: Claim) -> dict:
    return {"id":c.id,"user_id":c.user_id,"task_id":c.task_id,
            "status":c.status.value,"claimed_at":c.claimed_at.isoformat(),
            "expires_at":c.expires_at.isoformat()}

def _get_current_user_id(db: Session) -> str:
    # TODO: replace with real JWT auth dependency
    u = db.query(User).first()
    if not u: raise HTTPException(401,"not authenticated")
    return u.id

@router.post("/", status_code=201)
def create_claim(body: ClaimCreate, db: Session=Depends(get_db)):
    user_id = _get_current_user_id(db)
    task = db.query(Task).filter(Task.id==body.task_id).first()
    if not task: raise HTTPException(404,"task not found")
    if task.status.value not in ("open","claimed"):
        raise HTTPException(409, f"task is {task.status.value}, cannot claim")
    # Check existing active claim by this user
    existing = db.query(Claim).filter(
        Claim.user_id==user_id, Claim.task_id==body.task_id,
        Claim.status==ClaimStatus.active).first()
    if existing: raise HTTPException(409,"already have active claim on this task")
    now = datetime.now(timezone.utc)
    c = Claim(id=str(uuid.uuid4()), user_id=user_id, task_id=body.task_id,
              status=ClaimStatus.active, claimed_at=now,
              expires_at=now + timedelta(hours=CLAIM_WINDOW_HOURS))
    task.status = TaskStatus.claimed
    db.add(c); db.commit(); db.refresh(c)
    return _claim_out(c)

@router.delete("/{claim_id}", status_code=204)
def withdraw_claim(claim_id: str, db: Session=Depends(get_db)):
    user_id = _get_current_user_id(db)
    c = db.query(Claim).filter(Claim.id==claim_id, Claim.user_id==user_id).first()
    if not c: raise HTTPException(404,"claim not found")
    if c.status != ClaimStatus.active: raise HTTPException(409,"claim not active")
    c.status = ClaimStatus.withdrawn
    # Re-open task if no other active claims
    other = db.query(Claim).filter(
        Claim.task_id==c.task_id, Claim.status==ClaimStatus.active,
        Claim.id!=claim_id).first()
    if not other:
        task = db.query(Task).filter(Task.id==c.task_id).first()
        if task: task.status = TaskStatus.open
    db.commit()

@router.get("/mine")
def my_claims(db: Session=Depends(get_db)):
    user_id = _get_current_user_id(db)
    claims = db.query(Claim).filter(
        Claim.user_id==user_id, Claim.status==ClaimStatus.active).all()
    return [_claim_out(c) for c in claims]
