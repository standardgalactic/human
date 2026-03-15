#!/usr/bin/env python3
"""assemble_site.py — compile Zebrapedia articles into a static HTML site.

Reads:
    data/wiki/<stem>/corpus_graph.json
    data/wiki/<stem>/articles/<theme_slug>/<style>.json

Writes:
    data/wiki/<stem>/site/index.html
    data/wiki/<stem>/site/<theme_slug>/index.html
    data/wiki/<stem>/site/graph.html
    data/wiki/<stem>/site/timeline.html
    data/wiki/<stem>/site/style.css

Usage:
    python3 wiki/assemble_site.py \
        --wiki-dir data/wiki/<stem> \
        --title    "My Project"
"""

import argparse
import json
import re
from pathlib import Path

# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
:root {
  --bg: #0f0f1a;
  --surface: #16162a;
  --border: #2a2a44;
  --text: #d8d8e8;
  --muted: #7070a0;
  --accent: #6688ff;
  --accent2: #ffdd44;
  --open: #ff6655;
  --resolved: #44ff88;
  --font: 'Georgia', serif;
  --mono: 'Courier New', monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: var(--font);
       line-height: 1.7; font-size: 16px; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Layout */
.wrapper { max-width: 1100px; margin: 0 auto; padding: 0 2rem; }
header { border-bottom: 1px solid var(--border); padding: 1.5rem 0; }
header h1 { font-size: 1.4rem; color: var(--accent2); letter-spacing: .05em; }
header .sub { font-size: .85rem; color: var(--muted); margin-top: .2rem; }
nav { display: flex; gap: 1.5rem; padding: .8rem 0; border-bottom: 1px solid var(--border); }
nav a { font-size: .85rem; color: var(--muted); }
nav a:hover { color: var(--text); }
main { display: grid; grid-template-columns: 220px 1fr; gap: 2rem;
       padding: 2rem 0; }
aside { font-size: .85rem; }
aside h3 { color: var(--muted); text-transform: uppercase;
           font-size: .75rem; letter-spacing: .1em; margin-bottom: .75rem; }
aside ul { list-style: none; }
aside li { margin-bottom: .4rem; }
article { min-width: 0; }
article h2 { font-size: 1.5rem; color: var(--accent2); margin-bottom: .5rem; }
article .summary { color: var(--muted); font-size: .95rem;
                   margin-bottom: 1.5rem; border-left: 3px solid var(--border);
                   padding-left: 1rem; }

/* Style tabs */
.tabs { display: flex; gap: .5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.tab { padding: .3rem .9rem; border: 1px solid var(--border); border-radius: 3px;
       font-size: .8rem; cursor: pointer; color: var(--muted);
       background: var(--surface); transition: all .15s; }
.tab.active, .tab:hover { border-color: var(--accent); color: var(--accent); }
.tab-content { display: none; }
.tab-content.active { display: block; }

/* Sections */
.section { margin-bottom: 1.8rem; }
.section-heading { font-size: .75rem; text-transform: uppercase;
                   letter-spacing: .12em; color: var(--accent);
                   margin-bottom: .5rem; font-family: var(--mono); }
.section p { color: var(--text); }

/* Tags */
.tags { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: 1rem; }
.tag { font-size: .75rem; padding: .15rem .5rem;
       background: var(--surface); border: 1px solid var(--border);
       border-radius: 2px; color: var(--muted); }

/* Stats bar */
.stats { display: flex; gap: 2rem; padding: .8rem 0;
         border-top: 1px solid var(--border);
         border-bottom: 1px solid var(--border); margin-bottom: 1.5rem; }
.stat { font-size: .8rem; color: var(--muted); }
.stat span { color: var(--accent2); font-weight: bold; }

/* Cross-links */
.crosslinks { margin-top: 1.5rem; }
.crosslinks h4 { font-size: .75rem; text-transform: uppercase;
                 letter-spacing: .1em; color: var(--muted); margin-bottom: .5rem; }
.crosslinks a { font-size: .85rem; margin-right: .8rem; }

/* Ambiguity cards */
.amb-card { background: var(--surface); border: 1px solid var(--border);
            border-radius: 4px; padding: .75rem 1rem; margin-bottom: .75rem; }
.amb-label { font-size: .9rem; font-weight: bold; }
.amb-status { font-size: .75rem; padding: .1rem .4rem; border-radius: 2px;
              display: inline-block; margin-left: .5rem; }
.amb-status.open     { background: #3a1a1a; color: var(--open); }
.amb-status.resolved { background: #1a3a2a; color: var(--resolved); }
.amb-poss { font-size: .8rem; color: var(--muted); margin-top: .3rem; }

/* Index grid */
.index-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px,1fr));
              gap: 1rem; }
.index-card { background: var(--surface); border: 1px solid var(--border);
              border-radius: 4px; padding: 1rem; transition: border-color .15s; }
.index-card:hover { border-color: var(--accent); }
.index-card h3 { font-size: 1rem; margin-bottom: .4rem; }
.index-card p { font-size: .8rem; color: var(--muted); }

footer { border-top: 1px solid var(--border); padding: 1rem 0;
         font-size: .75rem; color: var(--muted); margin-top: 2rem; }
"""

# ── HTML helpers ──────────────────────────────────────────────────────────────

def page(title: str, site_title: str, nav_links: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — {site_title}</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
<div class="wrapper">
<header>
  <h1>⌘ {site_title}</h1>
  <div class="sub">zebragraph · predation-resistant knowledge atlas</div>
</header>
<nav>{nav_links}</nav>
<main>
{body}
</main>
<footer>Generated by <a href="https://github.com/zebragraph">zebragraph</a>.
Canonical semantic extraction · ten projections · four article styles.</footer>
</div>
<script>
document.querySelectorAll('.tab').forEach(tab => {{
  tab.addEventListener('click', () => {{
    const group = tab.closest('.tab-group');
    group.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    group.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    group.querySelector('#' + tab.dataset.target).classList.add('active');
  }});
}});
</script>
</body>
</html>"""


def nav(current: str = "") -> str:
    links = [
        ("index.html", "Index"),
        ("graph.html", "Graph"),
        ("timeline.html", "Timeline"),
        ("ambiguities.html", "Ambiguities"),
    ]
    return " ".join(
        f'<a href="/{href}"{"style=\"color:var(--text)\"" if current==href else ""}>{label}</a>'
        for href, label in links
    )


def slug(text: str) -> str:
    return re.sub(r"[^\w]", "_", text.lower())[:50]


def crosslinks_html(links: list, all_slugs: set) -> str:
    if not links:
        return ""
    items = []
    for name in links:
        s = slug(name)
        if s in all_slugs:
            items.append(f'<a href="/{s}/">{name}</a>')
        else:
            items.append(f'<span style="color:var(--muted)">{name}</span>')
    return f'<div class="crosslinks"><h4>See also</h4>{"".join(items)}</div>'


# ── Page builders ─────────────────────────────────────────────────────────────

def build_article_page(theme_label: str, articles: dict,
                       site_title: str, all_slugs: set) -> str:
    """Build an article page with four style tabs."""

    style_order = ["science", "mathematical", "artistic", "construction"]
    style_labels = {
        "science":      "Science",
        "mathematical": "Mathematical",
        "artistic":     "Artistic",
        "construction": "Construction",
    }

    first_valid = next(
        (s for s in style_order if s in articles and "sections" in articles[s]), None
    )
    if not first_valid:
        return f"<aside></aside><article><h2>{theme_label}</h2><p>No articles generated.</p></article>"

    summary = articles[first_valid].get("summary", "")
    all_tags = []
    for a in articles.values():
        all_tags.extend(a.get("tags", []))
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in dict.fromkeys(all_tags))

    # Stats bar
    stats_html = ""  # will be filled by caller with graph stats

    # Tabs
    tabs_html = '<div class="tab-group">'
    tabs_html += '<div class="tabs">'
    for i, style in enumerate(style_order):
        if style not in articles:
            continue
        active = "active" if style == first_valid else ""
        tabs_html += f'<div class="tab {active}" data-target="tab_{style}">{style_labels[style]}</div>'
    tabs_html += "</div>"

    for style in style_order:
        if style not in articles:
            continue
        art = articles[style]
        active = "active" if style == first_valid else ""
        tabs_html += f'<div class="tab-content {active}" id="tab_{style}">'

        if "error" in art:
            tabs_html += f'<p style="color:var(--open)">Error: {art["error"]}</p>'
        else:
            for sec in art.get("sections", []):
                tabs_html += f'''<div class="section">
<div class="section-heading">{sec["heading"]}</div>
<p>{sec["body"]}</p>
</div>'''
            cl_html = crosslinks_html(art.get("cross_links", []), all_slugs)
            tabs_html += cl_html

        tabs_html += "</div>"
    tabs_html += "</div>"

    body = f"""<aside>
<h3>Article</h3>
<ul>
<li><a href="/">← Index</a></li>
</ul>
</aside>
<article>
<h2>{theme_label}</h2>
<div class="summary">{summary}</div>
{tabs_html}
<div class="tags">{tags_html}</div>
</article>"""

    return page(theme_label, site_title, nav(), body)


def build_index_page(themes: list, graph: dict, site_title: str) -> str:
    stats = graph.get("stats", {})
    stats_html = f"""<div class="stats">
<div class="stat">entities <span>{stats.get("entities",0)}</span></div>
<div class="stat">events <span>{stats.get("events",0)}</span></div>
<div class="stat">claims <span>{stats.get("claims",0)}</span></div>
<div class="stat">ambiguities <span>{stats.get("ambiguities",0)}</span></div>
<div class="stat">themes <span>{stats.get("themes",0)}</span></div>
<div class="stat">source documents <span>{stats.get("source_documents",0)}</span></div>
</div>"""

    cards = ""
    for theme in themes:
        s = slug(theme["label"])
        cards += f"""<a href="/{s}/" class="index-card">
<h3>{theme["label"]}</h3>
<p>{len(theme.get("members",[]))} nodes</p>
</a>"""

    body = f"""<aside>
<h3>Navigation</h3>
<ul>
<li><a href="/graph.html">Constraint graph</a></li>
<li><a href="/timeline.html">Timeline</a></li>
<li><a href="/ambiguities.html">Ambiguities</a></li>
</ul>
</aside>
<article>
<h2>Knowledge Atlas</h2>
{stats_html}
<div class="index-grid">{cards}</div>
</article>"""

    return page("Index", site_title, nav("index.html"), body)


def build_ambiguities_page(graph: dict, site_title: str) -> str:
    ambs = graph.get("ambiguities", [])
    cards = ""
    for a in ambs:
        status = a.get("status", "open")
        poss = ", ".join(a.get("possibilities", [])[:5])
        cards += f"""<div class="amb-card">
<div class="amb-label">{a["label"]}
  <span class="amb-status {status}">{status}</span>
</div>
<div class="amb-poss">{poss or "no explicit possibilities recorded"}</div>
</div>"""

    body = f"""<aside>
<h3>Filters</h3>
<ul>
<li><a href="/?status=open">Open only</a></li>
<li><a href="/?status=resolved">Resolved only</a></li>
</ul>
</aside>
<article>
<h2>Ambiguity Register</h2>
<p class="summary">All underdetermined elements extracted from the corpus.
Open ambiguities represent interpretation space not yet collapsed by the text.</p>
<br>
{cards or "<p>No ambiguities recorded.</p>"}
</article>"""

    return page("Ambiguities", site_title, nav("ambiguities.html"), body)


def build_timeline_page(graph: dict, site_title: str) -> str:
    events_by_id = {e["id"]: e for e in graph.get("events", [])}
    timeline = graph.get("timeline", [])

    rows = ""
    for entry in timeline:
        eid = entry.get("event_id", "")
        evt = events_by_id.get(eid, {})
        label = evt.get("label", eid)
        basis = (evt.get("textual_basis") or [""])[0][:60]
        rows += f"""<tr>
<td style="color:var(--muted);font-family:var(--mono);font-size:.8rem;
    padding:.4rem .8rem;border-bottom:1px solid var(--border)">{entry.get("index","")}</td>
<td style="padding:.4rem .8rem;border-bottom:1px solid var(--border)">{label}</td>
<td style="font-size:.8rem;color:var(--muted);padding:.4rem .8rem;
    border-bottom:1px solid var(--border)">{basis}</td>
</tr>"""

    body = f"""<aside></aside>
<article>
<h2>Timeline</h2>
<p class="summary">Events ordered by narrative time across the corpus.</p><br>
<table style="width:100%;border-collapse:collapse">
<thead><tr>
<th style="text-align:left;padding:.4rem .8rem;color:var(--muted);font-size:.75rem">#</th>
<th style="text-align:left;padding:.4rem .8rem;color:var(--muted);font-size:.75rem">Event</th>
<th style="text-align:left;padding:.4rem .8rem;color:var(--muted);font-size:.75rem">Basis</th>
</tr></thead>
<tbody>{rows or "<tr><td colspan='3'>No timeline entries.</td></tr>"}</tbody>
</table>
</article>"""

    return page("Timeline", site_title, nav("timeline.html"), body)


def build_graph_page(graph: dict, site_title: str) -> str:
    """Build a D3-powered interactive force graph page."""

    nodes_data = []
    for ent in graph.get("entities", []):
        nodes_data.append({"id": ent["id"], "label": ent["name"][:30], "type": "entity"})
    for evt in graph.get("events", []):
        nodes_data.append({"id": evt["id"], "label": evt["label"][:30], "type": "event"})
    for clm in graph.get("claims", []):
        nodes_data.append({"id": clm["id"], "label": clm["text"][:30], "type": "claim"})

    edges_data = [
        {"source": r["source"], "target": r["target"],
         "label": r.get("relation", r.get("type", ""))}
        for r in graph.get("relations", [])
    ]

    nodes_json = json.dumps(nodes_data[:300])   # cap for browser performance
    edges_json = json.dumps(edges_data[:500])

    body = f"""<aside></aside>
<article style="grid-column:1/-1">
<h2>Constraint Graph</h2>
<p class="summary" style="margin-bottom:1rem">
Interactive force-directed graph of the corpus semantic network.
Drag nodes to explore. Colour: blue = entity, orange = event, green = claim.</p>
<div id="graph" style="width:100%;height:600px;background:var(--surface);
     border:1px solid var(--border);border-radius:4px"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const nodes = {nodes_json};
const links = {edges_json};
const TYPE_COLOR = {{ entity:"#4A90D9", event:"#E8A838", claim:"#7BC67E" }};

const el = document.getElementById('graph');
const W = el.clientWidth, H = el.clientHeight;

const svg = d3.select('#graph').append('svg')
  .attr('width', W).attr('height', H);

const sim = d3.forceSimulation(nodes)
  .force('link', d3.forceLink(links).id(d=>d.id).distance(80))
  .force('charge', d3.forceManyBody().strength(-120))
  .force('center', d3.forceCenter(W/2, H/2));

const link = svg.append('g').selectAll('line')
  .data(links).enter().append('line')
  .attr('stroke','#334').attr('stroke-width',1);

const node = svg.append('g').selectAll('circle')
  .data(nodes).enter().append('circle')
  .attr('r', 6)
  .attr('fill', d => TYPE_COLOR[d.type] || '#888')
  .call(d3.drag()
    .on('start', (e,d) => {{ if(!e.active) sim.alphaTarget(.3).restart(); d.fx=d.x;d.fy=d.y; }})
    .on('drag',  (e,d) => {{ d.fx=e.x; d.fy=e.y; }})
    .on('end',   (e,d) => {{ if(!e.active) sim.alphaTarget(0); d.fx=null;d.fy=null; }}));

const label = svg.append('g').selectAll('text')
  .data(nodes).enter().append('text')
  .text(d=>d.label).attr('font-size','9px').attr('fill','#aaa')
  .attr('dy','-.4em');

sim.on('tick', () => {{
  link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
      .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
  node.attr('cx',d=>d.x).attr('cy',d=>d.y);
  label.attr('x',d=>d.x).attr('y',d=>d.y);
}});
</script>
</article>"""

    return page("Constraint Graph", site_title, nav("graph.html"), body)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiki-dir", required=True)
    ap.add_argument("--title",    default="Zebrapedia")
    args = ap.parse_args()

    wiki_dir     = Path(args.wiki_dir)
    articles_dir = wiki_dir / "articles"
    corpus_graph_path = wiki_dir / "corpus_graph.json"
    site_dir     = wiki_dir / "site"
    site_dir.mkdir(parents=True, exist_ok=True)

    # Write CSS
    (site_dir / "style.css").write_text(CSS, encoding="utf-8")

    graph = {}
    if corpus_graph_path.exists():
        graph = json.loads(corpus_graph_path.read_text(encoding="utf-8"))

    themes = graph.get("themes", [])

    # Collect all theme slugs for cross-link resolution
    all_slugs = {slug(t["label"]) for t in themes}

    # Index page
    (site_dir / "index.html").write_text(
        build_index_page(themes, graph, args.title), encoding="utf-8"
    )

    # Ambiguity register
    (site_dir / "ambiguities.html").write_text(
        build_ambiguities_page(graph, args.title), encoding="utf-8"
    )

    # Timeline
    (site_dir / "timeline.html").write_text(
        build_timeline_page(graph, args.title), encoding="utf-8"
    )

    # Constraint graph
    (site_dir / "graph.html").write_text(
        build_graph_page(graph, args.title), encoding="utf-8"
    )

    # Article pages
    for theme in themes:
        theme_slug = slug(theme["label"])
        theme_dir  = articles_dir / theme_slug

        articles: dict[str, dict] = {}
        for style in ["science", "mathematical", "artistic", "construction"]:
            art_path = theme_dir / f"{style}.json"
            if art_path.exists():
                try:
                    articles[style] = json.loads(art_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass

        page_html = build_article_page(
            theme["label"], articles, args.title, all_slugs
        )

        page_dir = site_dir / theme_slug
        page_dir.mkdir(exist_ok=True)
        (page_dir / "index.html").write_text(page_html, encoding="utf-8")

    print(f"Site assembled: {site_dir}/")
    print(f"  index.html + {len(themes)} article pages + 3 utility pages")


if __name__ == "__main__":
    main()
