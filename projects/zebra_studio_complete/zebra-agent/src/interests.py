from pathlib import Path
TOPICS = {"math":["theorem","proof","equation"],"programming":["python","api","script","repo"],"art":["film","music","image","scene"],"philosophy":["meaning","ethics","ontology"]}
EXTS = {".md",".txt",".py",".tex",".js",".ts",".tsx",".html"}
def scan_interests(root="."):
    scores = {k:0 for k in TOPICS}
    for p in Path(root).rglob("*"):
        if p.is_file() and p.suffix.lower() in EXTS:
            text = p.read_text(encoding="utf-8", errors="ignore").lower()[:5000]
            for topic, words in TOPICS.items():
                scores[topic] += sum(text.count(w) for w in words)
    total = sum(scores.values()) or 1
    return {k: round(v/total, 3) for k,v in scores.items()}
