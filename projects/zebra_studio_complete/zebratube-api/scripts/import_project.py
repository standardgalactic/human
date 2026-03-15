#!/usr/bin/env python3
import argparse
from app.db import SessionLocal
from app.models.schema import Project, ProjectVersion
from app.services.import_tasks import import_tasks
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-id", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--project-version-id", required=True)
    ap.add_argument("--tasks-index", required=True)
    args = ap.parse_args()
    db = SessionLocal()
    p = db.get(Project, args.project_id)
    if not p:
        p = Project(id=args.project_id, title=args.title, project_type="repository"); db.add(p); db.commit()
    v = db.get(ProjectVersion, args.project_version_id)
    if not v:
        v = ProjectVersion(id=args.project_version_id, project_id=args.project_id, version_label="v1", graph_path=""); db.add(v); db.commit()
    import_tasks(args.tasks_index, db, args.project_version_id)
    print({"ok": True, "project_id": args.project_id})
    db.close()
if __name__ == "__main__": main()
