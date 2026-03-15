import json, sys
from pathlib import Path
query = sys.argv[1].lower(); root = Path(sys.argv[2]); hits = []
for p in root.rglob("graph.json"):
    data = json.loads(p.read_text(encoding="utf-8"))
    for k in ("entities","claims","themes"):
        for item in data.get(k, []):
            text = " ".join(str(v) for v in item.values()).lower()
            if query in text: hits.append({"file": str(p), "kind": k, "item": item})
print(json.dumps({"hits": hits[:50]}, indent=2, ensure_ascii=False))
