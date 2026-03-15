from pydantic import BaseModel

class ProjectOut(BaseModel):
    id: str
    title: str
    project_type: str | None = None

class ProjectCreate(BaseModel):
    id: str
    title: str
    project_type: str = "repository"
