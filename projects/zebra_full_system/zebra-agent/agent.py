
import json
from pathlib import Path

print("Zebra agent starting")

config = json.loads(Path("config.json").read_text())
print("API:", config["api"])
