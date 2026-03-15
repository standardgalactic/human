from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..deps import get_db
from ..models.schema import User
router = APIRouter(prefix="/users", tags=["users"])
@router.get("")
def list_users(db: Session = Depends(get_db)): return db.query(User).all()
