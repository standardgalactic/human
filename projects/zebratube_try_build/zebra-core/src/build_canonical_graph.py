import json, argparse
from pathlib import Path

KEYS = ["entities","events","relations","claims","ambiguities","transformations","timeline","themes"]

def dedupe(items, fields):
    seen = {}
    for item in items:
        k = tuple(item.get(f) for f in fields)
        if k not in seen:
            seen[k] = item
        else:
            old = seen[k]
            for fld, val in item.items():
                if isinstance(val, list):
                    old.setdefault(fld, [])
                    old[fld] += [x for x in val if x not in old[fld]]
    return list(seen.values())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-file", required=True)
    args = ap.parse_args()
    root = Path(args.input_dir)
    merged = {k: [] for k in KEYS}
    for p in sorted(root.glob("canonical_extract_*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        for k in KEYS:
            merged[k].extend(data.get(k, []))
    merged["entities"] = dedupe(merged["entities"], ["name","type"])
    merged["events"] = dedupe(merged["events"], ["label"])
    merged["relations"] = dedupe(merged["relations"], ["source","relation","target"])
    merged["claims"] = dedupe(merged["claims"], ["text"])
    merged["ambiguities"] = dedupe(merged["ambiguities"], ["label"])
    Path(args.output_file).write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
