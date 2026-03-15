
import json, pathlib

def generate_scripts(projection_json, out_dir):
    """Convert projection JSON into task script packages."""
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    data = json.load(open(projection_json))
    tasks = data.get("tasks", [])

    for t in tasks:
        task_dir = out / t["id"]
        task_dir.mkdir(exist_ok=True)

        (task_dir / "brief.md").write_text(f"# {t['title']}\n\n{t.get('description','')}")
        (task_dir / "script.txt").write_text(t.get("script",""))
        (task_dir / "nodes.json").write_text(json.dumps(t.get("nodes",[]), indent=2))
        (task_dir / "style_hints.txt").write_text(t.get("style",""))
        (task_dir / "dependencies.json").write_text(json.dumps(t.get("deps",[]), indent=2))
        (task_dir / "output_spec.json").write_text(json.dumps(t.get("output",{}), indent=2))
