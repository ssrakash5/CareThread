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

**AWS integration.** With `CARETHREAD_AI_PROVIDER=bedrock` (the default in
`backend/.env.example`) the backend uses:

- **Claude on Amazon Bedrock** for clinical document extraction
  (`backend/app/ai/extraction.py`) and as the evidence-matching judge
  (`backend/app/ai/matching.py`) — schema-enforced JSON via forced tool use.
- **Amazon Titan Text Embeddings v2** for chunk embeddings
  (`backend/app/ai/bedrock.py`), stored in a pgvector column.
- **Amazon S3** for raw artifact storage when `CARETHREAD_S3_BUCKET` is set
  (`backend/app/ai/storage.py`); local disk otherwise.
- **CockroachDB Cloud** (or local Postgres + pgvector) via `CARETHREAD_DATABASE_URL`.

Set `CARETHREAD_AI_PROVIDER=local` to run fully offline with the deterministic
regex/hash stand-ins that live alongside the Bedrock code — those are also
the automatic per-call fallback if a Bedrock request fails, so a demo never
hard-stops on a network blip (a warning is logged).

## Prerequisites

- Python 3.10+
- Node.js 18+
- Either a CockroachDB Cloud cluster or Docker (for local Postgres + pgvector)
- For `CARETHREAD_AI_PROVIDER=bedrock`: AWS credentials in the environment or
  `~/.aws/credentials` with Bedrock model access to a Claude model and
  `amazon.titan-embed-text-v2:0` in your region (plus S3 write access if
  you set a bucket)

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
cp .env.example .env                                 # then edit: DB URL, AI provider, S3 bucket
python seed.py                                       # drops+recreates tables, loads demo dataset (~3 min on Bedrock)
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

## AI pipeline (Bedrock)

Per ingested document (`app/ingestion/pipeline.py`):

1. Raw text → S3 (`app/ai/storage.py`).
2. Chunk → Titan v2 embeddings (256-d) → pgvector.
3. Claude extracts facts (`FOLLOWUP_RECOMMENDATION`, `FOLLOWUP_COMPLETED`,
   `STABLE_FINDING`, …) and structured incidental findings with anatomical
   location and follow-up interval — for any finding type, not just
   pulmonary nodules.
4. Rule-based scoring (same patient, location, finding type, embedding
   similarity) produces explainable signals; Claude then judges each open
   thread and returns `match_confidence`, clinician-readable `reasons`,
   `relationship_type` (`COMPLETION_EVIDENCE` / `STATUS_UPDATE` / …) and
   whether the obligation is fulfilled.
5. The agent proposes `LINK_EVIDENCE` / `CLOSE_THREAD` / `OPEN_THREAD` as
   `PENDING` actions only — a clinician approves in the UI.

Model IDs are configuration (`CARETHREAD_BEDROCK_MODEL_ID`,
`CARETHREAD_BEDROCK_EMBED_MODEL_ID`); switching to a newer Claude once your
AWS account has access is a one-line `.env` change.

## What's mocked / deferred

- **Auth**: demo RBAC via `X-User-Id` / `X-User-Role` headers
  (`app/security/roles.py`), not real authentication.
- **Deployment**: backend/frontend run locally; no IaC yet.

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
