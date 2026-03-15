from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..deps import get_db
from ..models.schema import Project, ProjectVersion, Task
from ..schemas.projects import ProjectOut, ProjectCreate
router = APIRouter(prefix="/projects", tags=["projects"])
@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    rows = db.query(Project).all(); out=[]
    for p in rows:
        versions = db.query(ProjectVersion).filter(ProjectVersion.project_id == p.id).all()
        vids = [v.id for v in versions]
        count = db.query(Task).filter(Task.project_version_id.in_(vids), Task.status=="open").count() if vids else 0
        out.append({"id": p.id, "title": p.title, "project_type": p.project_type, "open_tasks": count})
    return out
@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    obj = Project(id=payload.id, title=payload.title, project_type=payload.project_type)
    db.add(obj); db.commit(); db.refresh(obj)
    return {"id": obj.id, "title": obj.title, "project_type": obj.project_type, "open_tasks": 0}
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    return {"id": p.id, "title": p.title, "project_type": p.project_type, "open_tasks": 0}
