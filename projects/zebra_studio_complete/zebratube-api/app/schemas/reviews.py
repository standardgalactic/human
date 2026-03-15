from pydantic import BaseModel
class ReviewIn(BaseModel): submission_id: str; reviewer_id: str = "demo-user"; verdict: str; notes: str = ""
