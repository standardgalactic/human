
Zebra System Prototype

Components:

zebra-core
    corpus crawler and script generator

zebra-agent
    local worker node that selects tasks

zebratube-api
    FastAPI backend serving tasks

zebratube-web
    minimal frontend

scripts
    convenience launchers

Run:

1 start API
2 run zebra-core pipeline
3 run agent
4 open frontend
