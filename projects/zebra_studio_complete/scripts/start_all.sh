#!/usr/bin/env bash
set -e
(cd zebratube-api && uvicorn app.main:app --reload &) 
sleep 2
(cd zebratube-web && npm install && npm run dev &)
echo "API and web launched."
