import json, sys
from pathlib import Path

root = Path(sys.argv[1])
terms = {}
for p in root.rglob("*.md"):
    text = p.read_text(encoding="utf-8", errors="ignore")
    for token in text.split():
        if token.istitle():
            terms[token] = terms.get(token, 0) + 1
print(json.dumps({"concepts": [{"label": k, "count": v} for k, v in sorted(terms.items(), key=lambda kv: -kv[1])[:50]]}, indent=2))
