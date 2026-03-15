#!/usr/bin/env python3

import argparse
import json
import requests
from pathlib import Path

SYSTEM = """You are a structural text analysis engine.
Return VALID JSON ONLY.
Do not include markdown fences or backticks.
Do not hallucinate visual details unless explicitly stated in the text.
If uncertain, use empty arrays and brief notes fields.
Be literal, sparse, and schema-faithful."""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()

    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    text = Path(args.input_file).read_text(encoding="utf-8")

    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt + "\n\nTEXT:\n" + text}
        ],
        "options": {
            "temperature": 0
        },
        "stream": False
    }

    r = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=300
    )
    r.raise_for_status()

    content = r.json()["message"]["content"].strip()

    # Strip markdown fences if model ignores instructions
    if content.startswith("```"):
        lines = content.splitlines()
        lines = [l for l in lines if not l.startswith("```")]
        content = "\n".join(lines).strip()

    parsed = json.loads(content)

    Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_file).write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Written: {args.output_file}")


if __name__ == "__main__":
    main()
