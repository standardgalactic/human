"""
main.py — ZebraTube FastAPI application entry point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import projects, tasks, claims, submissions, reviews, assemblies, users, search, agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: run DB migrations, init storage dirs
    yield
    # shutdown


app = FastAPI(
    title="ZebraTube API",
    version="0.1.0",
    description="Predation-resistant collaborative media platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(users.router,       prefix="/api/users",       tags=["users"])
app.include_router(projects.router,    prefix="/api/projects",    tags=["projects"])
app.include_router(tasks.router,       prefix="/api/tasks",       tags=["tasks"])
app.include_router(claims.router,      prefix="/api/claims",      tags=["claims"])
app.include_router(submissions.router, prefix="/api/submissions", tags=["submissions"])
app.include_router(reviews.router,     prefix="/api/reviews",     tags=["reviews"])
app.include_router(assemblies.router,  prefix="/api/assemblies",  tags=["assemblies"])
app.include_router(search.router,      prefix="/api/search",      tags=["search"])
app.include_router(agent.router,       prefix="/api/agent",       tags=["agent"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "zebratube-api"}


def start():
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
