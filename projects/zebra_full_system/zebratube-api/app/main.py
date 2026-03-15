
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status":"zebratube running"}

@app.get("/tasks")
def tasks():
    return [{"id":"task1","title":"Example scene","projection":"narrative"}]
