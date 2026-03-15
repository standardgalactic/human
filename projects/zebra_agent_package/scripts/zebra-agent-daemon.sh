
#!/bin/bash

while true
do
    echo "running zebra agent"
    python zebra-agent/agent.py
    sleep 300
done
