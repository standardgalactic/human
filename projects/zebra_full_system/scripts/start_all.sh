
#!/bin/bash

echo "Starting Zebra system"

cd zebratube-api
uvicorn app.main:app --reload &

echo "API started"

cd ../zebra-agent
python agent.py
