import argparse, json, requests
from pathlib import Path

SYSTEM = "Return valid JSON only. Preserve underspecification."

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--input-file", required=True)
    ap.add_argument("--output-file", required=True)
    args = ap.parse_args()

    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    text = Path(args.input_file).read_text(encoding="utf-8")
    payload = {
        "model": args.model,
        "messages": [
            {"role":"system","content":SYSTEM},
            {"role":"user","content": prompt + "\n\nTEXT:\n" + text},
        ],
        "stream": False,
        "options": {"temperature": 0}
    }
    r = requests.post("http://localhost:11434/api/chat", json=payload, timeout=300)
    r.raise_for_status()
    content = r.json()["message"]["content"].strip()
    parsed = json.loads(content)
    Path(args.output_file).write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
