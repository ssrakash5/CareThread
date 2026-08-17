# CareThread

Jurisdiction-aware care-continuity agent that detects unresolved follow-up
obligations in clinical documentation, links later evidence back to those
obligations, and maintains an auditable case until a clinician confirms
follow-up is complete. MVP scope: incidental pulmonary nodule follow-up.
Full product spec in `project.md`.

This build targets **local development only** — no AWS deployment yet.
Bedrock is stood in with a deterministic rule-based agent (`backend/app/agents`,
`backend/app/ingestion/extractors.py`); S3 is stood in with local disk
storage under `storage/artifacts/`; CockroachDB is stood in with Postgres +
pgvector (wire-compatible, same schema, easy to swap later).

## Prerequisites

- Docker (for local Postgres + pgvector)
- Python 3.10+
- Node.js 18+

## Run it

**1. Database**

```
docker run -d --name carethread-pg -e POSTGRES_USER=carethread \
  -e POSTGRES_PASSWORD=carethread -e POSTGRES_DB=carethread \
  -p 5434:5432 pgvector/pgvector:pg16
```

**2. Backend**

```
cd backend
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt     # Windows
python seed.py                                       # loads synthetic demo dataset
./.venv/Scripts/python -m uvicorn app.main:app --port 8000 --reload
```

API docs at http://localhost:8000/docs.

**3. Frontend**

```
cd frontend
npm install
npm run dev
```

App at http://localhost:3000 (or the next free port — Next.js will tell you
if 3000 is taken).

## What's implemented

Full MVP loop from spec section 33, end to end, driven by the seed script
and reproducible through the UI:

```
artifact ingested -> stored -> chunked -> embedded -> facts extracted
-> finding detected -> care gap detected -> thread PROPOSED
-> clinician approves -> OPEN/IN_PROGRESS -> owner assigned
-> later artifact ingested -> patient-scoped retrieval finds the thread
-> evidence linked -> closure proposed -> clinician approves -> CLOSED
-> full provenance visible in History & Provenance
```

Six screens per spec section 17-22: Dashboard, Thread Detail, Evidence
Match Review, Patient Memory, Clinician Review, History & Provenance.

Guardrails from spec section 26 are enforced in code, not just UI: all
vector/thread retrieval is patient-scoped (`WHERE patient_id = :id`), the
agent only ever writes `PENDING` `ProposedAction` rows — `approval_service.py`
is the sole place that mutates `care_threads` state — and every mutation
writes an immutable `ThreadEvent`.

## What's mocked / deferred

- **Agent reasoning**: rule-based (regex/keyword extraction + weighted
  scoring), not an LLM. Swap point is `app/ingestion/extractors.py` and
  `app/agents/matching_agent.py` — same call signatures, real Bedrock/Claude
  calls can replace the logic bodies later.
- **Embeddings**: deterministic local hashing-trick vectors
  (`app/ingestion/embeddings.py`), not Bedrock embeddings. Stored/queried
  through pgvector so a real embedding model is a drop-in swap.
- **Auth**: demo RBAC via `X-User-Id` / `X-User-Role` headers
  (`app/security/roles.py`), not real authentication.
- **Storage**: local disk instead of S3 (`app/ingestion/pipeline.py`).
- **Deployment**: none — Terraform/SAM, Bedrock, S3, and CockroachDB Cloud
  wiring are out of scope until explicitly requested.

## Layout

```
backend/app/
  models/        SQLAlchemy ORM — mirrors spec sections 6-9, 14-15
  ingestion/      extraction, chunking, mock embeddings, pipeline orchestration
  agents/         matching_agent (evidence <-> thread), action_agent (proposals)
  workflows/      thread_state_machine, approval_service (the only state mutator)
  api/            FastAPI routers
  security/       demo RBAC
backend/seed.py   synthetic demo dataset (Jane Doe + 2 distractor patients)
frontend/app/     Next.js screens (dashboard, threads, evidence, patients, review)
```
