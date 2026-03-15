
#!/bin/bash
INPUT=$1
WORKDIR=$2

mkdir -p $WORKDIR

echo "Pretend crawling corpus..."
echo "{}" > $WORKDIR/graph.json

mkdir -p $WORKDIR/tasks
echo '{"tasks":[{"id":"task1","title":"Example scene","projection":"narrative","assembly_weight":1.0}]}' > $WORKDIR/tasks/tasks_index.json

echo "Pipeline finished"
