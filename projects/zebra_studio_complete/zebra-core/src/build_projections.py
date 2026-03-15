import json, argparse
from pathlib import Path
def narrative(graph):
    return {"category":"narrative_film","scenes":[{"scene_id":e.get("id", e.get("label","scene")), "summary":e.get("label",""), "characters":e.get("participants",[]), "uncertain_details":[]} for e in graph.get("events",[])]}
def diagram(graph):
    nodes = []
    for k in ("entities","events","claims"):
        for item in graph.get(k, []):
            nodes.append({"id": item.get("id", item.get("name", item.get("label","node"))), "label": item.get("name", item.get("label", item.get("text",""))), "type": k[:-1]})
    return {"category":"diagrammatic_structure","nodes":nodes,"edges":graph.get("relations",[])}
def ambiguity(graph):
    return {"category":"ambiguity_diffusion","units":[{"label": a.get("label",""), "possibilities": a.get("possibilities",[]), "status": a.get("status","open")} for a in graph.get("ambiguities",[])]}
BUILDERS = {"narrative_film": narrative, "diagrammatic_structure": diagram, "ambiguity_diffusion": ambiguity}
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    graph = json.loads(Path(args.graph).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    for name, fn in BUILDERS.items():
        (out_dir / f"{name}.json").write_text(json.dumps(fn(graph), indent=2, ensure_ascii=False), encoding="utf-8")
if __name__ == "__main__": main()
