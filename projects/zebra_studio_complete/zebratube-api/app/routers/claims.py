from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import uuid4
from ..deps import get_db
from ..models.schema import Claim
from ..schemas.tasks import TaskClaimIn
router = APIRouter(prefix="/claims", tags=["claims"])
@router.post("")
def claim_task(payload: TaskClaimIn, db: Session = Depends(get_db)):
    obj = Claim(id=str(uuid4()), task_id=payload.task_id, user_id=payload.user_id, status="active")
    db.add(obj); db.commit(); db.refresh(obj)
    return {"id": obj.id, "task_id": obj.task_id, "user_id": obj.user_id, "status": obj.status}
