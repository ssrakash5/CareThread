# CareThread

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

CareThread is a jurisdiction-aware care-continuity agent. It watches
clinical documentation for follow-up obligations that get recommended and
then quietly dropped — most commonly an incidental finding on imaging that
never makes it into the discharge paperwork — and keeps that obligation
alive as an auditable case until a clinician confirms it's actually been
resolved.

---

## Contents

- [The problem](#the-problem)
- [What CareThread does](#what-carethread-does)
- [What it deliberately does not do](#what-it-deliberately-does-not-do)
- [Architecture](#architecture)
- [Current scope](#current-scope)
- [AWS services used](#aws-services-used)
- [Prerequisites](#prerequisites)
- [Run it](#run-it)
- [Configuration](#configuration-backendenv)
- [What's implemented](#whats-implemented)
- [AI pipeline (Bedrock)](#ai-pipeline-bedrock)
- [Family clusters (hereditary risk)](#family-clusters-hereditary-risk)
- [PDF and image ingestion](#pdf-and-image-ingestion)
- [Testing](#testing)
- [What's mocked / deferred](#whats-mocked--deferred)
- [Layout](#layout)
- [License](#license)

---

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

---

## Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'background': '#ffffff', 'mainBkg': '#f8fafb', 'primaryColor': '#e8f2f4', 'primaryTextColor': '#1e293b', 'primaryBorderColor': '#64748b', 'secondaryColor': '#f1f5f9', 'tertiaryColor': '#ffffff', 'lineColor': '#94a3b8'}, 'flowchart': {'nodeSpacing': 45, 'rankSpacing': 65, 'curve': 'basis'}}}%%
flowchart TB
    Clinician([Clinician])
    UI[Clinician Interface]
    API[API Layer]
    Ingest[Ingestion Pipeline]
    Review[Review]

    Clinician --> UI --> API
    API --> Ingest
    API --> Review

    subgraph Agents[Agent Layer]
        direction LR
        Action[Action Agent]
        Match[Matching Agent]
        Follow[Follow Up Agent]
        Family[Family Agent]
    end

    Ingest --> Action
    Ingest --> Match
    API --> Follow
    API --> Family

    Store[Document Store]
    Queue[Proposal Queue]
    Approve[Approval Service]
    Audit[Audit Log]
    Memory[(Persistent Memory)]

    Ingest --> Store
    Agents --> Queue
    Review --> Queue

    Queue --> Approve
    Approve --> Audit
    Approve --> Memory
    Ingest --> Memory
    Agents --> Memory
```

| Component | Responsibility |
|---|---|
| **Clinician Interface** | Upload documents, review proposals, approve or reject actions, inspect history |
| **API Layer** | Routes requests, enforces access rules, coordinates ingestion and review |
| **Ingestion Pipeline** | Store raw documents, extract text, chunk content, derive facts and findings |
| **Action Agent** | Detects care gaps and proposes opening or closing threads |
| **Matching Agent** | Links new documents to open obligations with scored evidence matches |
| **Follow Up Agent** | Scans overdue threads and proposes escalation |
| **Family Agent** | Flags hereditary risk patterns across consented relatives |
| **Proposal Queue** | Holds pending actions until a clinician decides |
| **Approval Service** | Sole path for state changes; validates transitions before writing |
| **Persistent Memory** | Obligations, evidence links, embeddings, structured clinical facts |
| **Audit Log** | Immutable record of every proposal, approval, rejection, and state change |

Every agent only ever proposes; the Approval Service is the single place
that mutates state, and every mutation is written to the Audit Log.

---

## Current scope

The MVP focuses on one workflow end to end: incidental pulmonary nodule
follow-up (plus a few additional demo threads — cardiac, thyroid, renal,
spine — for UI variety). That scope was chosen deliberately — narrow
enough to build and demo convincingly, general enough that the same
architecture (patient memory → obligation tracking → evidence matching →
bounded agent actions) extends to other kinds of dropped follow-up later.

**AWS integration.** With `CARETHREAD_AI_PROVIDER=bedrock` (the default in
`backend/.env.example`) extraction, matching and embeddings run on Amazon
Bedrock and raw artifacts land in S3 — see the table below. Set it to
`local` to run fully offline with deterministic regex/hash stand-ins; those
are also the automatic per-call fallback if a Bedrock request fails, so a
demo never hard-stops on a network blip (a warning is logged).

## AWS services used

| Service | Role in CareThread | Code |
|---|---|---|
| **Amazon Bedrock — Claude (Anthropic)** | (1) Clinical document extraction: facts, incidental findings, anatomical location, follow-up interval. (2) Evidence-matching judge: is a new document evidence for an open care thread — confidence, clinician-readable reasons, `COMPLETION_EVIDENCE` vs `STATUS_UPDATE`, obligation fulfilled or not. Called via the Anthropic SDK's `AnthropicBedrock` client with forced tool-use for schema-validated JSON. Model is configurable (`CARETHREAD_BEDROCK_MODEL_ID`, default `us.anthropic.claude-sonnet-4-5-20250929-v1:0`). | `backend/app/ai/extraction.py`, `backend/app/ai/matching.py`, `backend/app/ai/bedrock.py` |
| **Amazon Bedrock — Titan Text Embeddings v2** | 256-dim embeddings for every document chunk, stored in pgvector and used for patient-scoped semantic similarity during matching (`amazon.titan-embed-text-v2:0`, boto3 `bedrock-runtime`). | `backend/app/ai/bedrock.py`, `backend/app/ingestion/embeddings.py` |
| **Amazon S3** | Raw artifact storage. Each ingested document is written to `s3://<bucket>/artifacts/<patient_id>/<artifact_type>/<title>.txt` (private bucket, SSE-S3); the URI is recorded on the `artifacts` row. Falls back to local disk when `CARETHREAD_S3_BUCKET` is empty. | `backend/app/ai/storage.py` |
| **AWS IAM** | Credentials for all of the above — either explicit keys in `backend/.env` (`CARETHREAD_AWS_ACCESS_KEY_ID` / `SECRET`) or the standard AWS credential chain (`~/.aws/credentials`, env vars, instance role). | `backend/app/config.py` |

The database is **CockroachDB Cloud** (a Cockroach Labs service running on
AWS `us-east-1`); local Postgres + pgvector works as a drop-in alternative.
No AWS compute/deployment layer yet — backend and frontend run locally.

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- Either a CockroachDB Cloud cluster or Docker (for local Postgres + pgvector)
- For `CARETHREAD_AI_PROVIDER=bedrock`: AWS credentials in the environment or
  `~/.aws/credentials` with Bedrock model access to a Claude model and
  `amazon.titan-embed-text-v2:0` in your region (plus S3 write access if
  you set a bucket)

## Run it

**1. Database** — one of:

- *CockroachDB Cloud (what the team uses):* put the connection string in
  `backend/.env` as
  `CARETHREAD_DATABASE_URL=cockroachdb+psycopg2://USER:PASSWORD@HOST:26257/defaultdb?sslmode=verify-full`
  (note the `cockroachdb+psycopg2` scheme; TLS is verified with `certifi`,
  no `root.crt` download needed).
- *Local Postgres + pgvector:*
  ```
  docker run -d --name carethread-pg -e POSTGRES_USER=carethread \
    -e POSTGRES_PASSWORD=carethread -e POSTGRES_DB=carethread \
    -p 5434:5432 pgvector/pgvector:pg16
  ```
  and `CARETHREAD_DATABASE_URL=postgresql+psycopg2://carethread:carethread@localhost:5434/carethread`.

**2. Backend**

```
cd backend
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt     # Windows
cp .env.example .env                                 # then edit: DB URL, AI provider, AWS keys, S3 bucket
python seed.py                                       # DROPS + recreates tables, loads demo dataset (~3 min on Bedrock)
./.venv/Scripts/python -m uvicorn app.main:app --port 8002 --reload
```

API docs at http://localhost:8002/docs. (Any free port works — 8000/8001
are sometimes held by VS Code's port forwarding on Windows.)

> `seed.py` is a reset, not a start: it drops every table. If you are
> joining a shared database that is already seeded, skip it.

**Sharing the project with a teammate.** `backend/.env` is git-ignored and
holds every secret (DB URL, AWS keys, bucket). Send it out-of-band; they
copy it into `backend/`, run the backend, and everything (Bedrock, S3,
CockroachDB) works without their own AWS setup. Rotate the IAM key when
the hackathon is over.

**3. Frontend**

```
cd frontend
npm install
npm run dev
```

App at http://localhost:3000 (or the next free port — Next.js will tell you
if 3000 is taken). Create `frontend/.env.local` with
`NEXT_PUBLIC_API_BASE=http://localhost:8002` (or wherever the backend runs);
restart `npm run dev` after changing it.

## Configuration (`backend/.env`)

| Variable | Purpose | Default |
|---|---|---|
| `CARETHREAD_DATABASE_URL` | SQLAlchemy URL (`cockroachdb+psycopg2://…` or `postgresql+psycopg2://…`) | local Postgres |
| `CARETHREAD_AI_PROVIDER` | `bedrock` (Claude + Titan) or `local` (offline regex/hash stand-ins) | `local` |
| `CARETHREAD_AWS_REGION` | Bedrock/S3 region | `us-east-1` |
| `CARETHREAD_AWS_ACCESS_KEY_ID` / `CARETHREAD_AWS_SECRET_ACCESS_KEY` | Optional explicit AWS keys; empty = use the AWS credential chain | empty |
| `CARETHREAD_BEDROCK_MODEL_ID` | Claude model / inference-profile ID | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| `CARETHREAD_BEDROCK_EMBED_MODEL_ID` | Embedding model | `amazon.titan-embed-text-v2:0` |
| `CARETHREAD_EMBEDDING_DIM` | pgvector width (Titan v2: 256/512/1024). Changing it requires re-running `seed.py`. | `256` |
| `CARETHREAD_S3_BUCKET` | Bucket for raw artifacts; empty = local disk under `storage/artifacts/` | empty |

Every Bedrock/S3 call falls back to its local implementation on error and
logs a warning, so a network blip degrades quality rather than failing an
ingest.

---

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

## Family clusters (hereditary risk)

Patients can be grouped into a `FamilyGroup` with typed `FamilyRelationship`
rows (PARENT/CHILD/SIBLING). `app/agents/family_agent.py::analyze_family` is
the one sanctioned cross-patient read in the system — scoped to one
consented family, never across unrelated patients — and flags when ≥2 blood
relatives share the same `finding_type` + `anatomical_location` (e.g. the
same nodule location). It never diagnoses or writes state directly: it
proposes an `OPEN_THREAD` action for a `HEREDITARY_RISK_REVIEW` thread,
which flows through the existing approval machinery unchanged. Endpoints:
`GET /patients/{id}/family`, `GET /families/{id}`,
`POST /families/{id}/analyze`. `seed.py` includes two demo clusters — the
Doe family (Jane + Susan share a right-upper-lobe nodule → flagged) and the
Alvarez family (unrelated finding types → correctly not flagged).

## PDF and image ingestion

The pipeline isn't text-only: `ingest_artifact(..., raw_bytes=..., raw_ext=...,
mime_type=...)` stores the original binary (PDF or image) as the artifact of
record while still chunking/embedding/extracting from `text`.
`app/ingestion/pdf_utils.py` extracts text from real PDFs (`pypdf`) so a PDF
upload runs through the exact same extraction/matching path as a pasted
report. `IMAGE` artifacts (spec section 3: reference artifacts only, never
auto-interpreted) get their caption chunked + embedded for retrieval, but
skip fact/finding extraction and thread matching entirely.
`backend/demo_assets.py` generates a real demo PDF (via `reportlab`) and
placeholder CT-scan-style PNGs (via `Pillow`) that `seed.py` ingests for
Jane and Susan — not real imaging data, just enough to exercise binary
storage + pgvector embedding end to end.

---

## Testing

```
cd backend
pytest              # default suite: mock/local provider only, no AWS calls
pytest -m bedrock   # opt-in: exercises real Bedrock (needs backend/.env credentials)
```

`tests/conftest.py` drops + recreates the schema against whatever database
`backend/.env` points at (same "demo DB, no migrations" policy as
`seed.py`) — don't point it at a database you care about keeping.
`tests/test_e2e_mock.py` walks the full MVP definition-of-done sequence
(spec section 33) through the HTTP API; `tests/test_family_agent.py` covers
the hereditary-risk flag and its false-positive-avoidance case.

## What's mocked / deferred

- **Auth**: demo RBAC via `X-User-Id` / `X-User-Role` headers
  (`app/security/roles.py`), not real authentication.
- **Deployment**: backend/frontend run locally; no IaC yet.

## Layout

```
backend/app/
  models/        SQLAlchemy ORM — patients, artifacts, findings, threads, evidence, actions, events, family
  ai/            AWS integrations — bedrock.py (Claude + Titan clients), extraction.py,
                 matching.py (LLM judge), storage.py (S3 + local binary storage)
  ingestion/     chunking, provider dispatch for extraction/embeddings, pdf_utils.py, pipeline orchestration
  agents/        matching_agent (rule signals + Claude judge), action_agent, family_agent (hereditary risk)
  workflows/      thread_state_machine, approval_service (the only state mutator)
  api/            FastAPI routers (incl. families.py)
  security/       demo RBAC
backend/seed.py   synthetic demo dataset (Jane Doe flagship case, family clusters, PDF/image artifacts)
backend/demo_assets.py  synthetic PDF/CT-scan-image generators used by seed.py
backend/tests/    pytest suite — mock e2e walk, family-agent tests, opt-in Bedrock tests
frontend/app/     Next.js screens (dashboard, threads, evidence, patients, review)
```

---

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for
the full text.
