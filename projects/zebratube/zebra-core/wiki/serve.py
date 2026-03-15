#!/usr/bin/env python3
"""serve.py — development server for a Zebrapedia static site.

Serves the site directory with automatic rebuild on source file changes.
Watches corpus_graph.json and articles/ for changes and rebuilds site.

Usage:
    python3 wiki/serve.py \
        --wiki-dir data/wiki/<stem> \
        --title    "My Project" \
        --port     8080
"""

import argparse
import http.server
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ── file watcher ──────────────────────────────────────────────────────────────

def mtimes(paths: list[Path]) -> dict[str, float]:
    result = {}
    for p in paths:
        try:
            result[str(p)] = p.stat().st_mtime
        except FileNotFoundError:
            pass
    return result


def watch_and_rebuild(wiki_dir: Path, title: str, interval: float = 2.0):
    """Background thread: watch for changes and rebuild site."""
    watch_targets = []

    # Watch corpus graph
    cg = wiki_dir / "corpus_graph.json"
    if cg.exists():
        watch_targets.append(cg)

    # Watch all article JSON files
    articles_dir = wiki_dir / "articles"
    if articles_dir.exists():
        watch_targets.extend(articles_dir.rglob("*.json"))

    prev = mtimes(watch_targets)

    while True:
        time.sleep(interval)

        # Refresh article file list
        if articles_dir.exists():
            current_targets = [cg] + list(articles_dir.rglob("*.json"))
        else:
            current_targets = [cg] if cg.exists() else []

        curr = mtimes(current_targets)

        changed = any(
            curr.get(k) != prev.get(k)
            for k in set(curr) | set(prev)
        )

        if changed:
            print(f"\n[zebra serve] change detected — rebuilding site…")
            try:
                subprocess.run(
                    [sys.executable, str(ROOT / "wiki" / "assemble_site.py"),
                     "--wiki-dir", str(wiki_dir), "--title", title],
                    check=True, capture_output=True,
                )
                print(f"[zebra serve] site rebuilt ✓")
            except subprocess.CalledProcessError as e:
                print(f"[zebra serve] rebuild failed: {e.stderr.decode()[:200]}")
            prev = curr


# ── HTTP server ───────────────────────────────────────────────────────────────

class SiteHandler(http.server.SimpleHTTPRequestHandler):
    """Serve static files with clean URL support (no .html extension needed)."""

    def translate_path(self, path):
        # Strip query string
        path = path.split("?")[0].split("#")[0]
        # Decode percent-encoding
        import urllib.parse
        path = urllib.parse.unquote(path)

        result = super().translate_path(path)

        # If path doesn't exist as-is, try appending /index.html
        if not Path(result).exists():
            candidate = Path(result) / "index.html"
            if candidate.exists():
                return str(candidate)
            candidate2 = Path(str(result) + ".html")
            if candidate2.exists():
                return str(candidate2)

        return result

    def log_message(self, fmt, *args):
        # Suppress routine GET logging for a cleaner terminal
        if args and str(args[1]) not in ("200", "304"):
            super().log_message(fmt, *args)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki-dir", required=True)
    ap.add_argument("--title",    default="Zebrapedia")
    ap.add_argument("--port",     type=int, default=8080)
    ap.add_argument("--no-watch", action="store_true",
                    help="disable live rebuild on file changes")
    args = ap.parse_args()

    wiki_dir = Path(args.wiki_dir).resolve()
    site_dir = wiki_dir / "site"

    if not site_dir.exists():
        print(f"[zebra serve] site not found at {site_dir}")
        print(f"  run: zebra wiki --stem {wiki_dir.name} first")
        sys.exit(1)

    # Change to site directory so SimpleHTTPRequestHandler serves from there
    os.chdir(site_dir)

    # Start watcher thread
    if not args.no_watch:
        watcher = threading.Thread(
            target=watch_and_rebuild,
            args=(wiki_dir, args.title),
            daemon=True,
        )
        watcher.start()
        print(f"[zebra serve] watching {wiki_dir} for changes")

    # Start HTTP server
    handler = SiteHandler
    server  = http.server.HTTPServer(("localhost", args.port), handler)

    print(f"[zebra serve] serving {site_dir}")
    print(f"[zebra serve] open  →  http://localhost:{args.port}/")
    print(f"[zebra serve] stop  →  Ctrl-C\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[zebra serve] stopped")


if __name__ == "__main__":
    main()
