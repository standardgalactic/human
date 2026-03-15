
#!/bin/bash

chmod +x scripts/zebra-agent-daemon.sh
nohup scripts/zebra-agent-daemon.sh > zebra-agent.log 2>&1 &
echo $! > zebra-agent.pid
echo "zebra agent started"
