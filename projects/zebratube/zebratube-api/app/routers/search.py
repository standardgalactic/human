"""
routers/search.py — corpus graph and task search
"""
import json
import pathlib
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db import get_db
from app.models.schema import Task, Project, ProjectVersion

router = APIRouter()

@router.get("/")
def search(q: str=Query(...,min_length=1), mode: str=Query(default="full"),
    project_id: Optional[str]=None, limit: int=Query(default=10,le=50),
    db: Session=Depends(get_db)):
    results = []
    terms = q.lower().split()
    # Search tasks by label
    task_q = db.query(Task)
    if project_id:
        task_q = task_q.join(ProjectVersion).filter(ProjectVersion.project_id==project_id)
    for t in task_q.limit(200).all():
        score = sum(1 for term in terms if term in t.label.lower()) / max(1,len(terms))
        if score > 0:
            results.append({"type":"task","id":t.id,"label":t.label,
                "project_id":None,"score":score,"source_docs":[]})
    # Search projects by title/description
    for p in db.query(Project).filter(Project.is_public==True).limit(50).all():
        text = f"{p.title} {p.description or ''}".lower()
        score = sum(1 for term in terms if term in text) / max(1,len(terms))
        if score > 0:
            results.append({"type":"project","id":p.id,"label":p.title,
                "project_id":p.id,"score":score,"source_docs":[]})
    # Sort by score, return top N
    results.sort(key=lambda r: -r["score"])
    return results[:limit]
