
import json, pathlib

def generate(index_file):
    data = json.loads(pathlib.Path(index_file).read_text())
    for t in data["tasks"]:
        print("Generate script for:", t["title"])

if __name__ == "__main__":
    generate("tasks_index.json")
