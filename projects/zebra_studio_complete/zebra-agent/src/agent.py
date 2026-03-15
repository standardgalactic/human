import json, argparse
from .hardware import detect_hardware
from .interests import scan_interests
from .api_client import ZebraAPI
from .scheduler import choose_tasks
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan-dir", default=".")
    ap.add_argument("--config", default="config.json")
    args = ap.parse_args()
    cfg = json.load(open(args.config))
    api = ZebraAPI(cfg["api"], cfg["user"])
    hw = detect_hardware()
    interests = scan_interests(args.scan_dir)
    tasks = api.get_tasks()
    selected = choose_tasks(tasks, hw, interests)
    print(json.dumps({"hardware": hw, "interests": interests, "selected": selected}, indent=2))
    if cfg.get("auto_claim"):
        for t in selected[:cfg.get("auto_claim_count",1)]:
            print(api.claim_task(t["id"]))
if __name__ == "__main__": main()
