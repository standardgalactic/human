
import json
from pathlib import Path

def ingest(project_dir):
    tasks_dir = Path(project_dir) / "tasks"
    tasks = []
    for f in tasks_dir.glob("*.json"):
        tasks.append(json.loads(f.read_text()))
    return tasks
