"""
routers/users.py — registration, profile, ledger
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.db import get_db
from app.models.schema import User, UserRole, PointLedger

router = APIRouter()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

def _user_out(u: User) -> dict:
    return {"id":u.id,"username":u.username,"role":u.role.value,
            "point_balance":u.point_balance,"person_graph_public":u.person_graph_public,
            "created_at":u.created_at.isoformat()}

@router.post("/register", status_code=201)
def register(body: UserRegister, db: Session=Depends(get_db)):
    if db.query(User).filter(User.username==body.username).first():
        raise HTTPException(409,"username taken")
    if db.query(User).filter(User.email==body.email).first():
        raise HTTPException(409,"email already registered")
    u = User(id=str(uuid.uuid4()), username=body.username, email=body.email,
             hashed_password=pwd_ctx.hash(body.password), role=UserRole.contributor)
    db.add(u); db.commit(); db.refresh(u)
    return _user_out(u)

@router.get("/me")
def me(db: Session=Depends(get_db)):
    u = db.query(User).first()  # TODO: real JWT
    if not u: raise HTTPException(401,"not authenticated")
    return {**_user_out(u), "specialisations":[], "contributions":{}, "person_graph":None}

@router.get("/{username}")
def get_user(username: str, db: Session=Depends(get_db)):
    u = db.query(User).filter(User.username==username).first()
    if not u: raise HTTPException(404,"user not found")
    return {**_user_out(u), "specialisations":[], "contributions":{}, "person_graph":None}

@router.get("/{username}/ledger")
def user_ledger(username: str, db: Session=Depends(get_db)):
    u = db.query(User).filter(User.username==username).first()
    if not u: raise HTTPException(404,"user not found")
    entries = db.query(PointLedger).filter(PointLedger.user_id==u.id)               .order_by(PointLedger.created_at.desc()).limit(50).all()
    return [{"id":e.id,"event_type":e.event_type.value,"delta":e.delta,
             "balance_after":e.balance_after,"task_id":e.task_id,
             "description":e.description,"created_at":e.created_at.isoformat()}
            for e in entries]
