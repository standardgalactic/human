#!/usr/bin/env python3

import sys
from pathlib import Path

MAX_CHARS = 6000

def split_paragraphs(text):
    return [p.strip() for p in text.split("\n\n") if p.strip()]

def main():
    input_file = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    text = input_file.read_text(encoding="utf-8")
    paragraphs = split_paragraphs(text)

    chunks = []
    current = []
    size = 0

    for p in paragraphs:
        if size + len(p) > MAX_CHARS and current:
            chunks.append("\n\n".join(current))
            current = [p]
            size = len(p)
        else:
            current.append(p)
            size += len(p)

    if current:
        chunks.append("\n\n".join(current))

    for i, chunk in enumerate(chunks):
        (out_dir / f"chunk_{i:03d}.txt").write_text(chunk, encoding="utf-8")

    print(f"Wrote {len(chunks)} chunks to {out_dir}")

if __name__ == "__main__":
    main()
