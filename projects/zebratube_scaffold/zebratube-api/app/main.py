
from fastapi import FastAPI
from .routers import projects, tasks, claims, submissions, reviews, assemblies, users, search

app = FastAPI(title="ZebraTube API")

app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(claims.router)
app.include_router(submissions.router)
app.include_router(reviews.router)
app.include_router(assemblies.router)
app.include_router(users.router)
app.include_router(search.router)
