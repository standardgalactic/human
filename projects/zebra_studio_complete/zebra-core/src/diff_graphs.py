import json, sys
from pathlib import Path
a = json.loads(Path(sys.argv[1]).read_text()); b = json.loads(Path(sys.argv[2]).read_text())
def names(items, key): return {x.get(key) for x in items}
out = {"entities_added": sorted(list(names(b.get("entities",[]),"name") - names(a.get("entities",[]),"name")))}
print(json.dumps(out, indent=2))
