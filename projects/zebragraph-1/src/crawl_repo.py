#!/usr/bin/env python3
"""crawl_repo.py — walk a repository and collect natural-language documents.

Produces a manifest JSON listing every document with metadata, and writes
each document as a plain-text file ready for canonical extraction.

Usage:
    python3 src/crawl_repo.py <repo_dir> <output_dir> [--stem STEM]

Output:
    <output_dir>/manifest.json          list of all collected documents
    <output_dir>/docs/<slug>.txt        normalised plain-text per document
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

# File extensions considered to contain natural language
TEXT_EXTENSIONS = {
    ".md", ".txt", ".rst", ".tex", ".org",
    ".ipynb", ".html", ".htm",
    ".py", ".js", ".ts", ".sh", ".yaml", ".yml", ".toml", ".json",
}

# Extensions we extract comments/docstrings from rather than full content
CODE_EXTENSIONS = {".py", ".js", ".ts", ".sh"}

# Never descend into these directories
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__",
    ".venv", "venv", "env", ".env", "dist", "build", ".cache",
    ".idea", ".vscode",
}

# Skip files larger than this (bytes)
MAX_FILE_BYTES = 200_000


def git_log(path: Path) -> str:
    """Return ISO date of last commit touching this file, or empty string."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci", "--", str(path)],
            capture_output=True, text=True, cwd=path.parent, timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def extract_code_prose(text: str, ext: str) -> str:
    """Extract docstrings and comments from code files."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # Python/JS/TS: comments and string literals that look like docs
        if stripped.startswith("#") or stripped.startswith("//"):
            lines.append(stripped.lstrip("#/").strip())
        elif stripped.startswith('"""') or stripped.startswith("'''"):
            lines.append(stripped.strip('"\' '))
    return "\n".join(lines) if lines else text[:2000]


def extract_notebook(text: str) -> str:
    """Extract markdown and output cells from a Jupyter notebook."""
    try:
        nb = json.loads(text)
        parts = []
        for cell in nb.get("cells", []):
            ct = cell.get("cell_type", "")
            src = "".join(cell.get("source", []))
            if ct == "markdown":
                parts.append(src)
            elif ct == "code" and src.strip():
                parts.append(f"[code]\n{src[:500]}")
        return "\n\n".join(parts)
    except Exception:
        return text[:3000]


def normalise(path: Path) -> str:
    """Return plain text content suitable for semantic extraction."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

    if path.suffix == ".ipynb":
        return extract_notebook(raw)
    if path.suffix in CODE_EXTENSIONS:
        return extract_code_prose(raw, path.suffix)
    # Strip HTML tags for .html files
    if path.suffix in (".html", ".htm"):
        return re.sub(r"<[^>]+>", " ", raw)
    return raw


def slug(path: Path, repo_root: Path) -> str:
    """Stable filesystem-safe identifier for a document."""
    rel = str(path.relative_to(repo_root))
    safe = re.sub(r"[^\w\-]", "_", rel)
    h = hashlib.md5(rel.encode()).hexdigest()[:6]
    return f"{safe[:60]}_{h}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_dir")
    ap.add_argument("output_dir")
    ap.add_argument("--stem", default=None)
    args = ap.parse_args()

    repo = Path(args.repo_dir).resolve()
    out = Path(args.output_dir)
    docs_dir = out / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    manifest = []

    for path in sorted(repo.rglob("*")):
        # Skip directories
        if not path.is_file():
            continue
        # Skip hidden and build directories
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue

        content = normalise(path)
        if len(content.strip()) < 50:
            continue

        doc_slug = slug(path, repo)
        doc_path = docs_dir / f"{doc_slug}.txt"
        doc_path.write_text(content, encoding="utf-8")

        last_modified = git_log(path)

        manifest.append({
            "slug": doc_slug,
            "path": str(path.relative_to(repo)),
            "extension": path.suffix,
            "size_bytes": len(content.encode()),
            "last_modified_git": last_modified,
            "doc_file": str(doc_path.relative_to(out)),
        })

    manifest_path = out / "manifest.json"
    manifest_path.write_text(
        json.dumps({"repo": str(repo), "documents": manifest}, indent=2),
        encoding="utf-8",
    )

    print(f"Crawled {len(manifest)} documents → {out}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
