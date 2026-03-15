from pydantic import BaseModel
class AssemblyOut(BaseModel): id: str; project_version_id: str; status: str
