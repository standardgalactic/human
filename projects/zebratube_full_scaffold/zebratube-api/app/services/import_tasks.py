import json
from pathlib import Path
from sqlalchemy.orm import Session
from ..models.schema import Task, TaskDependency

def import_tasks(index_file: str, db: Session, project_version_id: str):
    data = json.loads(Path(index_file).read_text(encoding="utf-8"))
    for t in data.get("tasks", []):
        db.add(Task(
            id=t["id"],
            project_version_id=project_version_id,
            title=t["title"],
            projection=t["projection"],
            difficulty=t.get("difficulty", "Standard"),
            assembly_weight=t.get("assembly_weight", 1.0),
            submission_count=0,
            status="open",
        ))
    db.commit()
    for t in data.get("tasks", []):
        for dep in t.get("deps", []):
            db.add(TaskDependency(task_id=t["id"], depends_on_task_id=dep))
    db.commit()
