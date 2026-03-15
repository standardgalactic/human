from fastapi import APIRouter, Depends, UploadFile, Form
from sqlalchemy.orm import Session
from uuid import uuid4
from pathlib import Path
from ..deps import get_db
from ..models.schema import Submission
from ..schemas.submissions import SubmissionOut

router = APIRouter(prefix="/submissions", tags=["submissions"])
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("", response_model=SubmissionOut)
async def create_submission(task_id: str = Form(...), user_id: str = Form("demo-user"), file: UploadFile | None = None, db: Session = Depends(get_db)):
    sid = str(uuid4())
    out = UPLOAD_DIR / f"{sid}_{file.filename}"
    content = await file.read()
    out.write_bytes(content)
    obj = Submission(id=sid, task_id=task_id, claim_id="", user_id=user_id, media_path=str(out), status="under_review")
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: str, db: Session = Depends(get_db)):
    return db.get(Submission, submission_id)
