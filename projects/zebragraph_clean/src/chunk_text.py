#!/usr/bin/env python3
"""chunk_text.py — split a text file into paragraph-preserving chunks.

Usage:
    python3 src/chunk_text.py <input_file> <output_dir>

Chunks are written as chunk_000.txt, chunk_001.txt, ...
MAX_CHARS controls the soft ceiling per chunk.
"""

import sys
from pathlib import Path

MAX_CHARS = 6000


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def build_chunks(paragraphs: list[str], max_chars: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    size = 0

    for p in paragraphs:
        plen = len(p)
        if current and size + plen + 2 > max_chars:
            chunks.append("\n\n".join(current))
            current = [p]
            size = plen
        else:
            current.append(p)
            size += plen + 2

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: chunk_text.py <input_file> <output_dir>", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    text = input_path.read_text(encoding="utf-8")
    paragraphs = split_paragraphs(text)
    chunks = build_chunks(paragraphs, MAX_CHARS)

    for i, chunk in enumerate(chunks):
        out_path = out_dir / f"chunk_{i:03d}.txt"
        out_path.write_text(chunk, encoding="utf-8")

    print(f"Wrote {len(chunks)} chunk(s) to {out_dir}")


if __name__ == "__main__":
    main()
