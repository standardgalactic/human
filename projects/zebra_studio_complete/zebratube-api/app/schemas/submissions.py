from pydantic import BaseModel
class SubmissionOut(BaseModel): id: str; task_id: str; user_id: str; status: str
