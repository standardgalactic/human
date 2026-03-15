import json, pathlib, zipfile, argparse
import networkx as nx
def build_task(task_id, title, projection, script, nodes=None, difficulty="Standard", output_format="video", deps=None):
    return {"id": task_id, "title": title, "projection": projection, "script": script, "nodes": nodes or [], "difficulty": difficulty, "output": {"format": output_format}, "deps": deps or [], "style": projection.replace("_", " "), "description": script[:160]}
def projection_to_tasks(name, data):
    tasks = []
    if name == "narrative_film":
        for i, scene in enumerate(data.get("scenes", []), start=1):
            tasks.append(build_task(f"{name}_{i:03d}", scene.get("summary","Scene"), name, scene.get("summary",""), scene.get("characters",[])))
    elif name == "diagrammatic_structure":
        tasks.append(build_task(f"{name}_001", "Diagrammatic graph render", name, "Render the graph with labeled typed nodes and edges.", []))
    elif name == "ambiguity_diffusion":
        for i, unit in enumerate(data.get("units", []), start=1):
            tasks.append(build_task(f"{name}_{i:03d}", unit.get("label","Ambiguity"), name, "Visualize a possibility field collapsing under constraints.", []))
    else:
        tasks.append(build_task(f"{name}_001", name, name, f"Produce a media segment for {name}.", []))
    return tasks
def assign_dependencies(tasks):
    G = nx.DiGraph()
    for t in tasks: G.add_node(t["id"])
    for i, t in enumerate(tasks):
        if i > 0:
            G.add_edge(tasks[i-1]["id"], t["id"]); t["deps"].append(tasks[i-1]["id"])
    cent = nx.betweenness_centrality(G, normalized=True) if len(G) > 1 else {tasks[0]["id"]:0.0} if tasks else {}
    for t in tasks: t["assembly_weight"] = round(0.5 + 1.5 * cent.get(t["id"], 0.0), 3)
def write_task_package(task, out_dir):
    task_dir = out_dir / task["id"]; task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "brief.md").write_text(f"# {task['title']}\n\n{task.get('description','')}", encoding="utf-8")
    (task_dir / "script.txt").write_text(task["script"], encoding="utf-8")
    (task_dir / "nodes.json").write_text(json.dumps(task.get("nodes", []), indent=2), encoding="utf-8")
    (task_dir / "style_hints.txt").write_text(task.get("style",""), encoding="utf-8")
    (task_dir / "dependencies.json").write_text(json.dumps(task.get("deps", []), indent=2), encoding="utf-8")
    (task_dir / "output_spec.json").write_text(json.dumps(task.get("output", {}), indent=2), encoding="utf-8")
    (task_dir / "task.json").write_text(json.dumps(task, indent=2), encoding="utf-8")
    zip_path = out_dir / f"{task['id']}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in task_dir.iterdir(): z.write(f, arcname=f"{task['id']}/{f.name}")
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projections-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    proj_dir = pathlib.Path(args.projections_dir)
    out_dir = pathlib.Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    tasks = []
    for p in proj_dir.glob("*.json"):
        tasks.extend(projection_to_tasks(p.stem, json.loads(p.read_text(encoding="utf-8"))))
    assign_dependencies(tasks)
    for t in tasks: write_task_package(t, out_dir)
    (out_dir / "tasks_index.json").write_text(json.dumps({"tasks": tasks}, indent=2), encoding="utf-8")
if __name__ == "__main__": main()
