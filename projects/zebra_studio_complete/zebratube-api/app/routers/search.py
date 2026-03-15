from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..deps import get_db
from ..models.schema import SearchIndex
router = APIRouter(prefix="/search", tags=["search"])
@router.get("")
def search(q: str = Query(...), db: Session = Depends(get_db)):
    like = f"%{q}%"; rows = db.query(SearchIndex).filter(SearchIndex.label.like(like)).all()
    return [{"kind": r.kind, "label": r.label, "payload": r.payload} for r in rows]
