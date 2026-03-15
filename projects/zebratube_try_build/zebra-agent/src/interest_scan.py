import json, sys
from pathlib import Path

EXTS = {".md",".txt",".py",".tex",".js",".ts",".tsx",".html"}
TOPICS = {
    "math": ["theorem","lemma","proof","equation","matrix","category"],
    "programming": ["python","function","class","api","repo","script"],
    "art": ["poem","image","film","music","color","scene"],
    "philosophy": ["ontology","epistemic","meaning","ethics","mind"],
}

def scan(root: Path):
    counts = {k:0 for k in TOPICS}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in EXTS:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore").lower()[:5000]
            except Exception:
                continue
            for topic, words in TOPICS.items():
                counts[topic] += sum(text.count(w) for w in words)
    total = sum(counts.values()) or 1
    return {k: round(v/total, 3) for k, v in counts.items()}

if __name__ == "__main__":
    print(json.dumps(scan(Path(sys.argv[1])), indent=2))
