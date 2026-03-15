from pydantic import BaseModel

class TaskOut(BaseModel):
    id: str
    title: str
    projection: str
    difficulty: str | None = None
    assembly_weight: float = 1.0
    submission_count: int = 0

class TaskClaimIn(BaseModel):
    task_id: str
    user_id: str = "demo-user"
