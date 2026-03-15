#!/usr/bin/env python3
"""generate_articles.py — project corpus graph into Zebrapedia articles.

For each theme cluster in the corpus graph, generates four article styles:
science, mathematical, artistic, construction.

Each article is a JSON file under:
    <wiki_dir>/articles/<theme_slug>/<style>.json

Usage:
    python3 wiki/generate_articles.py \
        --corpus-graph data/wiki/<stem>/corpus_graph.json \
        --wiki-dir     data/wiki/<stem> \
        --model        granite4
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from call_ollama import call_ollama, SYSTEM_PROMPT, strip_fences  # noqa: E402

STYLES = ["science", "mathematical", "artistic", "construction"]

MAX_GRAPH_CHARS = 8000  # truncate graph extract sent to model


def slug(text: str) -> str:
    return re.sub(r"[^\w]", "_", text.lower())[:50]


def subgraph_for_theme(graph: dict, theme: dict) -> dict:
    """Extract the subgraph relevant to a given theme."""
    member_ids = set(theme.get("members", []))

    def includes(node: dict) -> bool:
        return node.get("id", "") in member_ids

    entities = [e for e in graph.get("entities", []) if includes(e)]
    events   = [e for e in graph.get("events",   []) if includes(e)
                or set(e.get("participants", [])) & member_ids]
    claims   = [c for c in graph.get("claims",   []) if includes(c)]
    ambigs   = [a for a in graph.get("ambiguities", [])
                if set(a.get("applies_to", [])) & member_ids]
    transf   = [t for t in graph.get("transformations", []) if includes(t)]
    rels     = [r for r in graph.get("relations", [])
                if r["source"] in member_ids or r["target"] in member_ids]

    return {
        "theme":           theme["label"],
        "entities":        entities,
        "events":          events,
        "claims":          claims,
        "ambiguities":     ambigs,
        "transformations": transf,
        "relations":       rels,
    }


def generate_article(subgraph: dict, style: str, model: str,
                     prompts_dir: Path) -> dict:
    prompt_file = prompts_dir / f"wiki_article_{style}.txt"
    if not prompt_file.exists():
        return {"style": style, "error": f"prompt not found: {prompt_file}"}

    prompt = prompt_file.read_text(encoding="utf-8")
    graph_text = json.dumps(subgraph, ensure_ascii=False)
    if len(graph_text) > MAX_GRAPH_CHARS:
        graph_text = graph_text[:MAX_GRAPH_CHARS] + "\n...(truncated)"

    user_msg = prompt + "\n" + graph_text

    try:
        raw = call_ollama(model, SYSTEM_PROMPT, user_msg)
        cleaned = strip_fences(raw)
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {"style": style, "error": f"JSON parse failed: {e}", "raw": raw[:500]}
    except SystemExit:
        return {"style": style, "error": "Ollama unreachable"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-graph", required=True)
    ap.add_argument("--wiki-dir",     required=True)
    ap.add_argument("--model",        default="granite4")
    ap.add_argument("--themes",       nargs="*", default=None,
                    help="limit to specific theme labels")
    args = ap.parse_args()

    graph = json.loads(Path(args.corpus_graph).read_text(encoding="utf-8"))
    wiki_dir = Path(args.wiki_dir)
    articles_dir = wiki_dir / "articles"
    prompts_dir  = ROOT / "prompts"

    themes = graph.get("themes", [])
    if not themes:
        print("WARNING: no themes in corpus graph — adding synthetic root theme")
        themes = [{
            "id": "thm_root",
            "label": graph.get("repo", "Repository") or "Repository",
            "members": [e["id"] for e in graph.get("entities", [])[:20]],
        }]

    if args.themes:
        themes = [t for t in themes if t["label"] in args.themes]

    print(f"Generating articles for {len(themes)} themes × {len(STYLES)} styles")

    for theme in themes:
        theme_slug = slug(theme["label"])
        theme_dir  = articles_dir / theme_slug
        theme_dir.mkdir(parents=True, exist_ok=True)

        subgraph = subgraph_for_theme(graph, theme)

        for style in STYLES:
            out_path = theme_dir / f"{style}.json"
            if out_path.exists():
                print(f"  skip (cached): {theme_slug}/{style}")
                continue

            print(f"  {theme_slug}/{style} …")
            article = generate_article(subgraph, style, args.model, prompts_dir)
            out_path.write_text(
                json.dumps(article, indent=2, ensure_ascii=False), encoding="utf-8"
            )

    print(f"Articles written to: {articles_dir}")


if __name__ == "__main__":
    main()
