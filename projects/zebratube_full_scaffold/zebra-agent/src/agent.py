import json, argparse
from .hardware_scan import scan as hardware_scan
from .interest_scan import scan as interest_scan

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan-dir", required=True)
    args = ap.parse_args()
    profile = {
        "hardware": hardware_scan(),
        "interests": interest_scan(__import__("pathlib").Path(args.scan_dir)),
    }
    print(json.dumps(profile, indent=2))

if __name__ == "__main__":
    main()
