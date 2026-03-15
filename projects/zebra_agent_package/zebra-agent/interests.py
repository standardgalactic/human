
from pathlib import Path

KEYWORDS = [
    "math","physics","ai","video",
    "animation","diagram","music",
    "film","essay","code"
]

def scan_interests(root="."):
    scores = {}

    for path in Path(root).rglob("*"):
        if path.is_file():
            name = path.name.lower()
            for k in KEYWORDS:
                if k in name:
                    scores[k] = scores.get(k,0) + 1

    return scores
