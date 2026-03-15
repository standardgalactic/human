from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import uuid4
from ..deps import get_db
from ..models.schema import Assembly, AssemblySegment
from ..schemas.assemblies import AssemblyOut
router = APIRouter(prefix="/assemblies", tags=["assemblies"])
@router.post("")
def create_assembly(project_version_id: str, db: Session = Depends(get_db)):
    obj = Assembly(id=str(uuid4()), project_version_id=project_version_id, status="draft")
    db.add(obj); db.commit(); db.refresh(obj); return obj
@router.post("/{assembly_id}/segments")
def add_segment(assembly_id: str, submission_id: str, order: int, db: Session = Depends(get_db)):
    db.add(AssemblySegment(assembly_id=assembly_id, submission_id=submission_id, segment_order=order)); db.commit(); return {"ok": True}
@router.get("/{assembly_id}", response_model=AssemblyOut)
def get_assembly(assembly_id: str, db: Session = Depends(get_db)): return db.get(Assembly, assembly_id)
