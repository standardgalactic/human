
import json
from hardware import detect_hardware
from interests import scan_interests
from scheduler import choose_tasks
from api_client import ZebraAPI

CONFIG_FILE = "config.json"

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def run():

    config = load_config()

    api = ZebraAPI(config["api"], config["user"])

    hw = detect_hardware()
    interests = scan_interests(config["scan_path"])

    tasks = api.get_tasks()

    selected = choose_tasks(tasks, hw, interests)

    print("hardware:", hw)
    print("interests:", interests)
    print("selected tasks:")

    for t in selected:
        print("-", t["title"])
        if config["auto_claim"]:
            api.claim_task(t["id"])

if __name__ == "__main__":
    run()
