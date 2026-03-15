from fastapi import FastAPI
from .models.schema import Base
from .db import engine
from .routers import projects, tasks, claims, submissions, reviews, assemblies, users, search

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ZebraTube API")

for router in (projects.router, tasks.router, claims.router, submissions.router, reviews.router, assemblies.router, users.router, search.router):
    app.include_router(router)

@app.get("/")
def health():
    return {"ok": True, "service": "zebratube-api"}
