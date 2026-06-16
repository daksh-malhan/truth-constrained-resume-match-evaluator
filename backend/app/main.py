from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import database
from .routers import admin, analyze, coach, health, runs

app = FastAPI(title="Truth-Constrained Resume Match Evaluator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    database.init_db()


app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(admin.router)
app.include_router(runs.router)
app.include_router(coach.router)

