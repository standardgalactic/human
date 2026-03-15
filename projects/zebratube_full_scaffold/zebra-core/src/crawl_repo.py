from pathlib import Path
import json, sys

TEXT_EXTS = {".md",".txt",".rst",".tex",".py",".js",".ts",".tsx",".html",".css",".json",".yaml",".yml"}

def scan(root: Path):
    out = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in TEXT_EXTS:
            out.append({"path": str(p.relative_to(root)), "size": p.stat().st_size})
    return out

def main():
    root = Path(sys.argv[1])
    print(json.dumps({"files": scan(root)}, indent=2))

if __name__ == "__main__":
    main()
