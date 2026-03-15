import json
from pathlib import Path
from ..models.schema import Task, TaskDependency, SearchIndex

def import_tasks(index_file: str, db, project_version_id: str):
    data = json.loads(Path(index_file).read_text(encoding="utf-8"))
    for t in data.get("tasks", []):
        if db.get(Task, t["id"]):
            continue
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
            exists = db.query(TaskDependency).filter(
                TaskDependency.task_id == t["id"],
                TaskDependency.depends_on_task_id == dep
            ).first()
            if not exists:
                db.add(TaskDependency(task_id=t["id"], depends_on_task_id=dep))
        db.add(SearchIndex(
            project_version_id=project_version_id,
            kind="task",
            label=t["title"],
            payload=json.dumps({"id": t["id"], "projection": t["projection"]})
        ))
    db.commit()
