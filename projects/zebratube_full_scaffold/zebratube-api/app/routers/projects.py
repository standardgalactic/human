from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..deps import get_db
from ..models.schema import Project
from ..schemas.projects import ProjectOut, ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()

@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    obj = Project(id=payload.id, title=payload.title, project_type=payload.project_type)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    return db.get(Project, project_id)
