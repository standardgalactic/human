#!/usr/bin/env bash
set -e
bash zebra-core/scripts/run_pipeline.sh zebra-core/examples/sample.txt zebra-core/work
(cd zebratube-api && python scripts/seed_demo.py)
(cd zebratube-api && python scripts/import_project.py --project-id demo --title "Demo Project" --project-version-id demo-v1 --tasks-index ../zebra-core/work/tasks/tasks_index.json)
echo "Demo data imported."
