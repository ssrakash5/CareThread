from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db import engine, Base, ensure_vector_support
from app.api import patients, artifacts, threads, actions, audit, families
import app.models  # noqa: F401 ensures models are registered on Base

app = FastAPI(title="CareThread API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    # Next.js picks a different port automatically when 3000 is taken (3001, 3002, ...),
    # so allow any localhost/127.0.0.1 port rather than hard-coding one.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router)
app.include_router(artifacts.router)
app.include_router(threads.router)
app.include_router(actions.router)
app.include_router(audit.router)
app.include_router(families.router)


@app.on_event("startup")
def on_startup():
    ensure_vector_support()
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
