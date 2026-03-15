from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import uuid4
from ..deps import get_db
from ..models.schema import Review
from ..schemas.reviews import ReviewIn

router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.post("")
def create_review(payload: ReviewIn, db: Session = Depends(get_db)):
    obj = Review(id=str(uuid4()), submission_id=payload.submission_id, reviewer_id=payload.reviewer_id, verdict=payload.verdict, notes=payload.notes)
    db.add(obj); db.commit(); db.refresh(obj)
    return {"id": obj.id, "verdict": obj.verdict}
