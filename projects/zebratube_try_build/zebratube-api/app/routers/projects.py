from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..deps import get_db
from ..models.schema import Project, ProjectVersion
from ..schemas.projects import ProjectOut, ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    rows = db.query(Project).all()
    out = []
    for p in rows:
        open_tasks = 0
        try:
            # lazy import to keep the file simple
            from ..models.schema import Task
            versions = db.query(ProjectVersion).filter(ProjectVersion.project_id == p.id).all()
            version_ids = [v.id for v in versions]
            if version_ids:
                open_tasks = db.query(Task).filter(Task.project_version_id.in_(version_ids), Task.status == "open").count()
        except Exception:
            open_tasks = 0
        out.append({"id": p.id, "title": p.title, "project_type": p.project_type, "open_tasks": open_tasks})
    return out

@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    obj = Project(id=payload.id, title=payload.title, project_type=payload.project_type)
    db.add(obj); db.commit(); db.refresh(obj)
    return {"id": obj.id, "title": obj.title, "project_type": obj.project_type, "open_tasks": 0}

@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    obj = db.get(Project, project_id)
    if not obj:
        return None
    return {"id": obj.id, "title": obj.title, "project_type": obj.project_type, "open_tasks": 0}
