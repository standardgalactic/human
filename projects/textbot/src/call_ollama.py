#!/usr/bin/env python3
"""call_ollama.py — send a prompt + text chunk to a local Ollama model.

Usage:
    python3 src/call_ollama.py \
        --model granite4 \
        --prompt-file prompts/canonical_extract.txt \
        --input-file data/chunks/essay/chunk_000.txt \
        --output-file data/analyses/essay/canonical_extract_chunk_000.json

The model is called with temperature=0 for deterministic structured output.
The response is expected to be a bare JSON object (no markdown fences).
If the model wraps output in ```json ... ``` the fence is stripped automatically.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
TIMEOUT = 300

SYSTEM_PROMPT = """\
You are a structural text analysis engine.
Return VALID JSON ONLY.
Do not use markdown code fences.
Do not add preamble or commentary.
If you are uncertain about a value, use an empty array or empty string.
Never invent facts not present in the input text.
"""


def strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers if present."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def call_ollama(model: str, system: str, user: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0},
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(
            f"ERROR: Cannot connect to Ollama at {OLLAMA_URL}. "
            "Is `ollama serve` running?",
            file=sys.stderr,
        )
        sys.exit(1)

    return r.json()["message"]["content"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--input-file", required=True)
    ap.add_argument("--output-file", required=True)
    args = ap.parse_args()

    prompt_template = Path(args.prompt_file).read_text(encoding="utf-8")
    input_text = Path(args.input_file).read_text(encoding="utf-8")

    user_message = prompt_template.rstrip() + "\n\nTEXT:\n" + input_text

    raw = call_ollama(args.model, SYSTEM_PROMPT, user_message)
    cleaned = strip_fences(raw)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"ERROR: Model returned invalid JSON: {e}", file=sys.stderr)
        print("--- Raw output ---", file=sys.stderr)
        print(raw[:2000], file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
