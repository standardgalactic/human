
#!/bin/bash

kill $(cat zebra-agent.pid)
rm zebra-agent.pid
echo "zebra agent stopped"
