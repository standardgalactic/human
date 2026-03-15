#!/usr/bin/env python3
"""
recycle.py — recursive corpus expansion pipeline

Takes completed media submissions (video transcripts, article texts, annotations),
runs them back through zebra canonical extraction, merges new nodes into the
existing corpus graph, and generates new tasks from the expanded graph.

This implements the recursive compilation cycle:
    text → graph → scripts → media → text → graph → …

Usage:
    python3 src/recycle.py \\
        --transcripts-dir  /path/to/transcripts \\
        --existing-graph   data/canonical/<stem>/graph.json \\
        --output-dir       data/canonical/<stem>_recycled \\
        --model            granite4

Transcripts can be:
    - Plain .txt files of video narration
    - .md files of article or annotation text
    - .json files with {"transcript": "...", "source_submission_id": "..."} 
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def collect_transcripts(transcripts_dir: Path) -> list[Path]:
    """Collect all transcript text files from a directory."""
    exts = {".txt", ".md", ".rst"}
    files = []
    for ext in exts:
        files.extend(transcripts_dir.rglob(f"*{ext}"))
    return sorted(files)


def extract_text_from_json(path: Path) -> str | None:
    """Extract text field from a JSON transcript file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("transcript") or data.get("text") or data.get("body")
    except (json.JSONDecodeError, Exception):
        return None


def run_extraction(
    transcript_path: Path,
    output_dir: Path,
    model: str,
    prompt_file: Path,
) -> Path | None:
    """Run canonical extraction on one transcript. Returns output JSON path."""
    stem = transcript_path.stem[:40]
    out_path = output_dir / f"canonical_extract_{stem}.json"

    if out_path.exists():
        print(f"  skip (cached): {out_path.name}")
        return out_path

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "src" / "call_ollama.py"),
                "--model",       model,
                "--prompt-file", str(prompt_file),
                "--input-file",  str(transcript_path),
                "--output-file", str(out_path),
            ],
            timeout=300,
        )
        if result.returncode == 0:
            return out_path
        else:
            print(f"  WARNING: extraction failed for {transcript_path.name}")
            return None
    except subprocess.TimeoutExpired:
        print(f"  WARNING: timeout on {transcript_path.name}")
        return None


def merge_into_existing(
    existing_graph_path: Path,
    new_analysis_dir: Path,
    output_path: Path,
) -> dict:
    """
    Merge new canonical extractions into the existing corpus graph.
    Returns the merged graph dict.
    """
    # Load existing graph
    existing = json.loads(existing_graph_path.read_text(encoding="utf-8"))

    # Run build_corpus_graph over new analyses + write temp manifest
    import tempfile, os
    manifest_data = {
        "repo": str(new_analysis_dir),
        "documents": [
            {"slug": p.stem, "path": p.name, "extension": ".txt",
             "size_bytes": p.stat().st_size, "last_modified_git": "",
             "doc_file": f"docs/{p.stem}.txt"}
            for p in new_analysis_dir.glob("canonical_extract_*.json")
        ]
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(manifest_data, f)
        manifest_path = f.name

    try:
        new_graph_path = new_analysis_dir / "_new_graph.json"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "src" / "build_corpus_graph.py"),
                "--analyses-dir", str(new_analysis_dir),
                "--manifest",     manifest_path,
                "--output-file",  str(new_graph_path),
            ],
            timeout=120,
        )
        if result.returncode != 0 or not new_graph_path.exists():
            print("WARNING: corpus graph build failed, using existing graph only")
            return existing
    finally:
        os.unlink(manifest_path)

    new_graph = json.loads(new_graph_path.read_text(encoding="utf-8"))

    # Merge node lists (union by dedup keys from build_canonical_graph)
    from app_compatible_merge import merge_graphs
    merged = merge_graphs(existing, new_graph)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return merged


def simple_merge_graphs(existing: dict, new_graph: dict) -> dict:
    """
    Simple merge: extend each node list, mark recycled nodes with source_docs.
    Does not deduplicate (done in build_canonical_graph). Used as fallback.
    """
    KEYS = ["entities", "events", "relations", "claims",
            "ambiguities", "transformations", "themes", "timeline"]
    merged = dict(existing)
    for key in KEYS:
        existing_items = list(existing.get(key, []))
        new_items = [
            {**item, "source_docs": item.get("source_docs", []) + ["recycled"]}
            for item in new_graph.get(key, [])
        ]
        merged[key] = existing_items + new_items
    merged["recycled_from"] = merged.get("recycled_from", []) + ["recycle_pass"]
    return merged


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcripts-dir",  required=True)
    ap.add_argument("--existing-graph",   required=True)
    ap.add_argument("--output-dir",       required=True)
    ap.add_argument("--model",            default="granite4")
    ap.add_argument("--run-scripts",      action="store_true",
                    help="also run zebra scripts after merging")
    args = ap.parse_args()

    transcripts_dir = Path(args.transcripts_dir)
    existing_graph  = Path(args.existing_graph)
    output_dir      = Path(args.output_dir)
    analysis_dir    = output_dir / "analyses"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    prompt_file = ROOT / "prompts" / "canonical_extract.txt"

    print(f"zebra recycle — {transcripts_dir}")

    # 1. Collect transcripts
    transcripts = collect_transcripts(transcripts_dir)

    # Also handle JSON transcripts
    for jp in transcripts_dir.rglob("*.json"):
        text = extract_text_from_json(jp)
        if text and len(text.strip()) > 100:
            txt_path = analysis_dir / f"{jp.stem}_extracted.txt"
            if not txt_path.exists():
                txt_path.write_text(text, encoding="utf-8")
            transcripts.append(txt_path)

    print(f"  {len(transcripts)} transcripts found")

    # 2. Extract canonical graphs from each transcript
    extracted = []
    for t in transcripts:
        out = run_extraction(t, analysis_dir, args.model, prompt_file)
        if out:
            extracted.append(out)

    print(f"  {len(extracted)} extractions complete")

    if not extracted:
        print("  No new extractions. Exiting.")
        return

    # 3. Merge into existing graph
    merged_path = output_dir / "graph_recycled.json"
    print(f"  merging into {existing_graph.name}…")

    try:
        new_graph_path = analysis_dir / "_new_graph.json"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "src" / "build_canonical_graph.py"),
                "--input-dir",   str(analysis_dir),
                "--output-file", str(new_graph_path),
            ],
            check=True, timeout=120,
        )
        existing = json.loads(existing_graph.read_text(encoding="utf-8"))
        new_graph = json.loads(new_graph_path.read_text(encoding="utf-8"))
        merged = simple_merge_graphs(existing, new_graph)
    except Exception as e:
        print(f"  WARNING: merge failed ({e}), using existing graph")
        merged = json.loads(existing_graph.read_text(encoding="utf-8"))

    merged_path.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  merged graph → {merged_path}")

    # 4. Optionally run script generation on the expanded graph
    if args.run_scripts:
        # First rebuild projections from merged graph
        proj_dir = output_dir / "projections"
        proj_dir.mkdir(exist_ok=True)
        for proj_name in [
            "narrative_film", "diagrammatic_structure", "ambiguity_diffusion",
            "timeline_causality", "structural_summary",
        ]:
            script_file = ROOT / "projections" / f"build_{proj_name}.py"
            if not script_file.exists():
                continue
            out_file = proj_dir / f"{proj_name}.json"
            with open(out_file, "w") as f:
                subprocess.run(
                    [sys.executable, str(script_file), str(merged_path)],
                    stdout=f, timeout=60,
                )

        # Then generate scripts
        scripts_dir = output_dir / "scripts"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "src" / "generate_scripts.py"),
                "--projections-dir", str(proj_dir),
                "--graph",           str(merged_path),
                "--output-dir",      str(scripts_dir),
            ],
            check=True, timeout=120,
        )
        print(f"  new scripts → {scripts_dir}")
        print(f"\n  next: import into database with:")
        print(f"    python3 -m app.workers.ingest_project \\")
        print(f"      --project-slug <slug> \\")
        print(f"      --scripts-dir  {scripts_dir} \\")
        print(f"      --graph-path   {merged_path}")

    print(f"\nRecycle complete. Expanded graph: {merged_path}")


if __name__ == "__main__":
    main()
