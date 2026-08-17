from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db import engine, Base
from app.api import patients, artifacts, threads, actions, audit
import app.models  # noqa: F401 ensures models are registered on Base

app = FastAPI(title="CareThread API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router)
app.include_router(artifacts.router)
app.include_router(threads.router)
app.include_router(actions.router)
app.include_router(audit.router)


@app.on_event("startup")
def on_startup():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
