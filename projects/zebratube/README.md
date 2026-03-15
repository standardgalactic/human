# ZebraTube

*A distributed compiler for knowledge. Texts compile into graphs. Graphs compile
into scripts. Scripts compile into media. Media compiles back into new texts.*

---

## What it is

ZebraTube inverts YouTube's logic. YouTube begins with finished videos and
organizes attention around them. ZebraTube begins with a canonical semantic
graph derived from a text or repository, and organizes contributors around
the structured production work required to realize that corpus as media.

The core object is not the video — it is the **task**: a claimable unit of
media production derived from a script, scene, diagram specification, or
voiceover segment, all generated automatically from the Zebra pipeline.

**Tagline:** *Download the script. Make the missing scene. Help assemble the film.*

---

## Architecture

```
zebra-core/         Text analysis engine (Python CLI)
zebratube-api/      Backend API (FastAPI + PostgreSQL)
zebratube-web/      Frontend (React + TypeScript + Vite)
```

### Pipeline

```
corpus / repository / text
    ↓  zebra crawl + zebra extract
canonical semantic graph
    ↓  zebra project + zebra scripts
task graph (scripts + zip bundles)
    ↓  python -m app.workers.ingest
database (tasks, bounties, dependencies)
    ↓  zebratube-web
contributors claim → upload media
    ↓  selectors compare alternatives
    ↓  assemblers place segments on timeline
    ↓  ffmpeg render
collaborative film / lecture / visual essay
    ↓  zebra recycle (transcripts back into pipeline)
expanded corpus graph → new tasks
```

---

## Quickstart (development)

### Prerequisites
- Python 3.11+
- Node 20+
- PostgreSQL 15+
- Ollama with granite4 model: `ollama pull granite4`
- ffmpeg: `brew install ffmpeg` or `apt install ffmpeg`

### 1. Start services

```bash
docker-compose up postgres redis
# or run postgres/redis natively
```

### 2. Set up the API

```bash
cd zebratube-api
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload
# API running at http://localhost:8000
```

### 3. Start the web dev server

```bash
cd zebratube-web
npm install
npm run dev
# Web running at http://localhost:3000
```

### 4. Ingest your first project

```bash
# Point zebra at any directory with text files
cd zebra-core

# Run the full pipeline on a repository
ollama serve &
./zebra/zebra crawl ~/my-project --stem myproject
./zebra/zebra scripts --stem myproject

# Import into the database
python3 -m app.workers.ingest \
  --project-slug myproject \
  --zebra-dir    data \
  --stem         myproject
```

Visit http://localhost:3000 — the project appears on the homepage map.

### 5. Start the recursive cycle

After contributors produce media:

```bash
# Feed transcripts and annotations back into the pipeline
./zebra/zebra recycle /path/to/transcripts --stem myproject
```

New tasks are generated from the expanded graph and imported automatically.

---

## Full Docker deployment

```bash
docker-compose up --build
```

Runs: postgres, redis, api (with migration), transcode worker, web.

---

## The ten zebra verbs

| Verb | What it does |
|------|-------------|
| `zebra extract <file>` | Canonical extraction → graph.json |
| `zebra project [all\|name]` | Build projections from graph |
| `zebra scripts` | Generate task scripts + zip bundles |
| `zebra crawl <dir>` | Crawl repo → corpus graph |
| `zebra wiki` | Generate Zebrapedia static site |
| `zebra serve` | Dev server with live reload |
| `zebra search <query>` | Query corpus graph |
| `zebra diff <a> <b>` | Compare two graph versions |
| `zebra person` | Build longitudinal intellectual graph |
| `zebra recycle <dir>` | Feed media back into pipeline |
| `zebra render [all\|name]` | Render projection visualizations |
| `zebra simulate constraints` | Run constraint propagation |

---

## Point economy

```
B(task) = base_value × log(1 + scarcity) × assembly_weight

scarcity        = 1 / (1 + submission_count)
assembly_weight = normalized betweenness centrality [0.5 – 2.0]
```

Tasks with zero submissions and high centrality earn maximum bounty.
Tasks with many alternatives earn near-zero, preventing redundant work.

---

## Philosophy

Most text-to-media systems are interpretive predators. They collapse a text
into a single realization immediately — the variable "traveler" becomes a
specific face, voice, age, and costume before the narrative has supplied
those constraints.

Zebra preserves the herd. The canonical semantic graph records ambiguity as
first-class objects. Ten projections show different structural patterns in the
same constraint field. None claims to be the canonical rendering, because
texts do not have canonical renderings.

ZebraTube scales this to a platform: texts and repositories are converted into
structured media tasks, contributors claim and fulfill those tasks, selectors
compare alternatives, assemblers integrate segments, and the resulting media
re-enters the pipeline as new text. The system is not a social network of
agents talking to each other but a distributed compiler for knowledge.
