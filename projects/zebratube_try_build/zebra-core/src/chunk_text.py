from pathlib import Path
import sys

MAX_CHARS = 6000

def split_paragraphs(text: str):
    return [p.strip() for p in text.split("\n\n") if p.strip()]

def main():
    input_file = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    text = input_file.read_text(encoding="utf-8")
    paras = split_paragraphs(text)
    current, current_len, chunks = [], 0, []
    for p in paras:
        if current and current_len + len(p) + 2 > MAX_CHARS:
            chunks.append("\n\n".join(current))
            current, current_len = [p], len(p)
        else:
            current.append(p)
            current_len += len(p) + 2
    if current:
        chunks.append("\n\n".join(current))
    for i, c in enumerate(chunks, start=1):
        (out_dir / f"chunk_{i:03d}.txt").write_text(c, encoding="utf-8")

if __name__ == "__main__":
    main()
