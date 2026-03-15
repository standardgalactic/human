from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..deps import get_db
from ..models.schema import Task
from ..schemas.tasks import TaskOut
router = APIRouter(prefix="/tasks", tags=["tasks"])
@router.get("", response_model=list[TaskOut])
def list_tasks(project_version_id: str | None = Query(None), db: Session = Depends(get_db)):
    q = db.query(Task)
    if project_version_id: q = q.filter(Task.project_version_id == project_version_id)
    return q.all()
@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)): return db.get(Task, task_id)
