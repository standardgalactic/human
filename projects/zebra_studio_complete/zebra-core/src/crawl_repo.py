from pathlib import Path
import json, sys
EXTS = {".md",".txt",".rst",".tex",".py",".js",".ts",".tsx",".html",".css",".json",".yaml",".yml"}
def main():
    root = Path(sys.argv[1])
    files = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in EXTS:
            files.append({"path": str(p.relative_to(root)), "size": p.stat().st_size})
    print(json.dumps({"files": files}, indent=2))
if __name__ == "__main__": main()
