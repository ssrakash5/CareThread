# CareThread

CareThread is a jurisdiction-aware care-continuity agent. It watches
clinical documentation for follow-up obligations that get recommended and
then quietly dropped — most commonly an incidental finding on imaging that
never makes it into the discharge paperwork — and keeps that obligation
alive as an auditable case until a clinician confirms it's actually been
resolved.

## The problem

A radiology report recommends a repeat scan in 6–12 months. The discharge
summary that follows doesn't mention it. Nobody is deliberately at fault —
the recommendation just didn't survive the handoff between systems and
visits. Months later, nobody is tracking whether that scan ever happened.

## What CareThread does

1. **Detects** unresolved follow-up recommendations in incoming clinical
   artifacts (radiology reports, discharge summaries, progress notes).
2. **Proposes** a CareThread — a persistent, trackable obligation — rather
   than letting the finding disappear once the encounter ends.
3. **Links** later evidence (a follow-up scan, a progress note mentioning
   pending imaging) back to the original obligation, scoped strictly to
   that one patient.
4. **Proposes** the next step — link evidence, escalate, extend the
   deadline, or close the thread — but never acts unilaterally.
5. **Requires clinician approval** for every consequential state change,
   and keeps a complete, provenance-linked audit trail of what happened
   and why.

## What it deliberately does not do

CareThread does not diagnose disease, determine malignancy, interpret
images automatically, message patients autonomously, or close a case on
its own. It coordinates follow-up based on clinician-authored evidence —
it's a memory and accountability layer for care obligations, not a
diagnostic tool.

## Current scope

The MVP focuses on one workflow end to end: incidental pulmonary nodule
follow-up (plus a few additional demo threads — cardiac, thyroid, renal,
spine — for UI variety). That scope was chosen deliberately — narrow
enough to build and demo convincingly, general enough that the same
architecture (patient memory → obligation tracking → evidence matching →
bounded agent actions) extends to other kinds of dropped follow-up later.

This build targets **local development only** — no AWS deployment yet.
Bedrock is stood in with a deterministic rule-based agent
(`backend/app/agents`, `backend/app/ingestion/extractors.py`); S3 is stood
in with local disk storage under `storage/artifacts/`; CockroachDB is
stood in with Postgres + pgvector (wire-compatible, same schema, easy to
swap later).

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
./.venv/Scripts/python -m uvicorn app.main:app --port 8001 --reload
```

API docs at http://localhost:8001/docs.

**3. Frontend**

```
cd frontend
npm install
npm run dev
```

App at http://localhost:3000 (or the next free port — Next.js will tell you
if 3000 is taken). Set `NEXT_PUBLIC_API_BASE` in `frontend/.env.local` to
match wherever the backend is running.

## What's implemented

Full MVP loop from the spec, end to end, driven by the seed script and
reproducible through the UI:

```
artifact ingested -> stored -> chunked -> embedded -> facts extracted
-> finding detected -> care gap detected -> thread PROPOSED
-> clinician approves -> OPEN/IN_PROGRESS -> owner assigned
-> later artifact ingested -> patient-scoped retrieval finds the thread
-> evidence linked -> closure proposed -> clinician approves -> CLOSED
-> full provenance visible in History & Provenance
```

Six screens: Dashboard, Thread Detail, Evidence Match Review, Patient
Memory, Clinician Review, History & Provenance.

Guardrails are enforced in code, not just UI: all vector/thread retrieval
is patient-scoped (`WHERE patient_id = :id`), the agent only ever writes
`PENDING` `ProposedAction` rows — `approval_service.py` is the sole place
that mutates `care_threads` state — and every mutation writes an immutable
`ThreadEvent`.

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
  models/        SQLAlchemy ORM — patients, artifacts, findings, threads, evidence, actions, events
  ingestion/      extraction, chunking, mock embeddings, pipeline orchestration
  agents/         matching_agent (evidence <-> thread), action_agent (proposals)
  workflows/      thread_state_machine, approval_service (the only state mutator)
  api/            FastAPI routers
  security/       demo RBAC
backend/seed.py   synthetic demo dataset (Jane Doe flagship case + several distractor/variety patients)
frontend/app/     Next.js screens (dashboard, threads, evidence, patients, review)
```
