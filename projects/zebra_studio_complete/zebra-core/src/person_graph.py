import json, sys
from pathlib import Path
root = Path(sys.argv[1]); terms = {}
for p in root.rglob("*.md"):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    for tok in txt.split():
        if tok.istitle(): terms[tok] = terms.get(tok, 0) + 1
print(json.dumps({"concepts":[{"label":k,"count":v} for k,v in sorted(terms.items(), key=lambda kv: -kv[1])[:30]]}, indent=2))
