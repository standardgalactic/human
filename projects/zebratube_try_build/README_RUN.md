# ZebraTube: try-build notes

This scaffold now includes a simple ingestion path from `zebra-core` task artifacts into the API.

## Suggested local run order

### 1. Generate tasks from a text or repository
From `zebra-core/` run:

```bash
bash scripts/run_pipeline.sh /path/to/input.txt work
```

This should produce:

```text
work/graph/graph.json
work/projections/*.json
work/tasks/tasks_index.json
```

### 2. Start the API
From `zebratube-api/` run:

```bash
python -m uvicorn app.main:app --reload
```

### 3. Seed a demo user
Use the seed script:

```bash
python scripts/seed_demo.py
```

### 4. Create a project and project version
You can do this by API request or the helper script:

```bash
python scripts/import_project.py   --project-id demo-proj   --title "Demo Project"   --project-version-id demo-v1   --tasks-index ../zebra-core/work/tasks/tasks_index.json
```

### 5. Start the frontend
From `zebratube-web/` run:

```bash
npm install
npm run dev
```

Then browse to the frontend and API.
