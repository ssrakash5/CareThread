Figma Screens link: https://www.figma.com/design/x1EwSFjwO1EP1pDQO4IALS/CareThread-Product-Screens?node-id=0-1&t=XZqV7CUGfVALh9uI-0

Hackathon link: https://cockroachdb-ai.devpost.com/?ref_feature=challenge&ref_medium=discover

Git Repo:git@github.com:ssrakash5/CareThread.git
Spec Sheet: 
Absolutely. I’d build **CareThread as a focused care-continuity product**, with multimodal memory underneath it rather than exposing a generic medical chatbot.

# CareThread — Product & Engineering Specification

## 1. Product definition

**CareThread** is a jurisdiction-aware care-continuity agent that detects unresolved follow-up obligations in clinical documentation, links later evidence back to those obligations, and maintains an auditable case until a clinician confirms that follow-up is complete.

The MVP should focus on **incidental radiology follow-up**, especially pulmonary nodules.

A representative workflow is:

> CT report recommends repeat imaging → discharge paperwork omits the recommendation → CareThread detects the gap → proposes a thread → clinician approves and assigns ownership → later evidence is matched to the thread → CareThread proposes escalation, extension, or closure → clinician approves the final state.

CareThread does **not** diagnose disease or independently determine whether a finding is benign or malignant. It coordinates follow-up based primarily on clinician-authored evidence.

---

# 2. Core system model

There are three conceptual layers.

| Layer                 | Responsibility                                                                |
| --------------------- | ----------------------------------------------------------------------------- |
| **Patient Memory**    | Stores and retrieves longitudinal multimodal patient evidence                 |
| **CareThread Engine** | Represents persistent unresolved care obligations                             |
| **Care Agent**        | Reasons across new evidence and existing threads and proposes bounded actions |

The product should always make this distinction visible. Patient Memory explains *what the system knows*. A CareThread explains *what still needs to happen*.

---

# 3. MVP scope

### Primary workflow

**Incidental pulmonary nodule follow-up**

Supported evidence should initially include:

* Radiology reports
* Discharge summaries
* PCP/progress notes
* Scheduling notes
* Patient messages
* Labs as context
* Medical images as reference artifacts only

Images should **not** be automatically interpreted diagnostically in the MVP. The actionable finding should originate from the associated radiology report.

### Explicitly out of scope

Do not implement cohort-wide semantic search, automatic diagnosis, autonomous patient messaging, automated image interpretation, treatment recommendations, or automatic clinical closure.

All consequential state changes require clinician approval.

---

# 4. Recommended architecture

```text
                     ┌──────────────────────────┐
                     │       CareThread UI      │
                     │      Next.js / React     │
                     └────────────┬─────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │        API Layer         │
                     │ FastAPI / Lambda / REST  │
                     └────────────┬─────────────┘
                                  │
               ┌──────────────────┼──────────────────┐
               │                  │                  │
               ▼                  ▼                  ▼
       ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
       │ Ingestion    │   │ Care Agent   │   │ Thread       │
       │ Pipeline     │   │              │   │ Workflow     │
       └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
              │                  │                  │
              ▼                  ▼                  ▼
       ┌────────────────────────────────────────────────────┐
       │                    CockroachDB                     │
       │                                                    │
       │ patients                                           │
       │ artifacts / chunks / embeddings                    │
       │ findings / care_threads / evidence_links           │
       │ thread_events / proposed_actions / approvals       │
       │ audit_events                                       │
       └──────────────────────┬─────────────────────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │    AWS S3     │
                      │ Raw artifacts │
                      └───────────────┘
```

For the hackathon/demo implementation, I would use:

| Component        | Technology                 |
| ---------------- | -------------------------- |
| Frontend         | Next.js + TypeScript       |
| Styling          | Tailwind CSS               |
| Backend          | Python FastAPI             |
| Compute          | AWS Lambda                 |
| Object storage   | Amazon S3                  |
| LLM              | Amazon Bedrock             |
| Embeddings       | Bedrock embedding model    |
| Database         | CockroachDB                |
| Vector retrieval | CockroachDB vector search  |
| Authentication   | Simple demo RBAC initially |
| Infrastructure   | AWS SAM or Terraform       |
| Charts/icons     | Lucide icons               |

Use **synthetic patient data** for the demo.

---

# 5. Data ingestion pipeline

Every clinical artifact enters through the same ingestion interface.

```text
UPLOAD / RECEIVE ARTIFACT
        │
        ▼
Store original in S3
        │
        ▼
Create artifact record
        │
        ▼
Extract text / metadata
        │
        ▼
Normalize clinical document
        │
        ▼
Chunk content
        │
        ▼
Generate embeddings
        │
        ▼
Store chunks + embeddings + provenance
        │
        ▼
Extract candidate findings / obligations
        │
        ▼
Search THIS PATIENT'S existing CareThreads
        │
        ▼
Propose:
   New Thread
   Link Evidence
   No Action
```

A crucial constraint should exist at the query layer:

```text
WHERE patient_id = :current_patient_id
```

Vector retrieval should never begin with unrestricted cohort-wide similarity search.

---

# 6. Core database schema

## `patients`

Represents the patient scope for every retrieval and workflow operation.

```text
patient_id
mrn
display_name
dob
jurisdiction
home_region
created_at
updated_at
```

---

## `artifacts`

One row per clinical artifact.

```text
artifact_id
patient_id
artifact_type
source_system
source_provider
document_date
s3_uri
mime_type
title
status
jurisdiction
created_at
```

Example `artifact_type` values:

```text
RADIOLOGY_REPORT
DISCHARGE_SUMMARY
PROGRESS_NOTE
LAB_RESULT
PATIENT_MESSAGE
IMAGE
SCHEDULING_NOTE
```

---

## `artifact_chunks`

Semantic retrieval unit.

```text
chunk_id
artifact_id
patient_id
chunk_index
chunk_text
embedding
section_name
page_number
created_at
```

Notice that `patient_id` is duplicated intentionally to make patient-scoped retrieval straightforward and efficient.

---

# 7. Provenance model

Every extracted claim should retain its source.

## `facts`

```text
fact_id
patient_id
artifact_id
chunk_id
fact_type
fact_text
normalized_value
confidence
extracted_at
```

Example:

```text
fact_type:
FOLLOWUP_RECOMMENDATION

fact_text:
Follow-up CT chest recommended in 6–12 months.

artifact:
CT Chest Without Contrast

section:
Impression

page:
2
```

The UI should be capable of showing:

> Follow-up CT recommended in 6–12 months
> **Source:** CT Chest · Impression · Page 2

Never show an agent-generated medical claim without the underlying evidence.

---

# 8. Findings

A finding represents a clinical observation appearing in evidence.

## `findings`

```text
finding_id
patient_id
finding_type
anatomical_location
finding_description
source_artifact_id
source_chunk_id
first_observed_at
latest_observed_at
status
created_at
```

Example:

```text
finding_type:
PULMONARY_NODULE

location:
RIGHT_UPPER_LOBE

description:
6 mm solid pulmonary nodule
```

---

# 9. CareThreads

This is the heart of the application.

## `care_threads`

```text
thread_id
patient_id
thread_type
title
finding_id
status
priority
owner_user_id
jurisdiction
home_region
opened_at
due_at
closed_at
closure_reason
created_by
updated_at
```

Example:

```text
thread_type:
INCIDENTAL_PULMONARY_FOLLOWUP

title:
Incidental Pulmonary Nodule Follow-up

status:
OPEN

due_at:
2026-10-15
```

---

# 10. Thread state machine

Use explicit workflow states rather than allowing the agent to invent statuses.

```text
PROPOSED
   │
   ├── clinician rejects ──► REJECTED
   │
   ▼
OPEN
   │
   ▼
IN_PROGRESS
   │
   ├────────────► AWAITING_EVIDENCE
   │                    │
   │                    ▼
   │                 OVERDUE
   │                    │
   │                    ▼
   │                 ESCALATED
   │
   ▼
CLOSURE_PROPOSED
   │
   ├── rejected ───────► OPEN
   │
   ▼
CLOSED
```

The agent may **propose** transitions.

The workflow service performs transitions only after permission and approval checks.

---

# 11. Evidence-to-thread linking

## `thread_evidence`

```text
thread_evidence_id
thread_id
artifact_id
chunk_id
relationship_type
match_score
match_reason
linked_by
linked_at
approval_status
```

Relationship types might include:

```text
INITIAL_FINDING
FOLLOWUP_RECOMMENDATION
MISSING_FOLLOWUP
SCHEDULING_EVIDENCE
COMPLETION_EVIDENCE
STATUS_UPDATE
```

---

# 12. Evidence matching agent

When new evidence arrives, retrieval should be:

```text
New artifact
     │
     ▼
Identify patient
     │
     ▼
Retrieve OPEN threads
     │
     ▼
Retrieve thread evidence
     │
     ▼
Semantic similarity
     +
structured signals
     │
     ▼
Agent match evaluation
```

The match should not rely on embeddings alone.

A proposed match can consider:

```text
same patient
same anatomical location
same finding type
similar terminology
follow-up interval
modality
temporal compatibility
existing thread status
```

Example output:

```json
{
  "thread_id": "thr_123",
  "match_confidence": 0.92,
  "reasons": [
    "same patient",
    "same right upper lobe nodule",
    "follow-up CT referenced",
    "timeline consistent"
  ],
  "recommended_action": "LINK_EVIDENCE"
}
```

---

# 13. Agent actions

The agent should operate through a very small action interface.

```text
propose_thread()
propose_evidence_link()
propose_assignment()
propose_extension()
propose_escalation()
propose_closure()
```

Do **not** give the production agent arbitrary database write access.

The workflow service validates and executes approved actions.

---

# 14. Proposed actions

## `proposed_actions`

```text
action_id
thread_id
patient_id
action_type
proposed_payload
reason
confidence
source_evidence
agent_run_id
status
created_at
reviewed_at
reviewed_by
```

Possible action types:

```text
OPEN_THREAD
LINK_EVIDENCE
ASSIGN_OWNER
EXTEND_DUE_DATE
ESCALATE_THREAD
CLOSE_THREAD
REOPEN_THREAD
```

Possible statuses:

```text
PENDING
APPROVED
REJECTED
EXPIRED
```

---

# 15. Audit history

Every meaningful action should produce an immutable event.

## `thread_events`

```text
event_id
thread_id
patient_id
event_type
actor_type
actor_id
previous_state
new_state
metadata
created_at
```

Example:

```text
THREAD_OPENED
OWNER_ASSIGNED
EVIDENCE_LINKED
REMINDER_GENERATED
DEADLINE_EXTENDED
ESCALATION_PROPOSED
CLOSURE_PROPOSED
THREAD_CLOSED
```

This table powers the **History & Provenance** screen.

---

# 16. User roles

Start with four roles.

| Role             | Capability                                      |
| ---------------- | ----------------------------------------------- |
| Clinician        | Approve consequential actions and close threads |
| Care Coordinator | Manage ownership, outreach and scheduling       |
| Administrator    | Configure organization and workflows            |
| Auditor          | Read-only access to history and provenance      |

Patient access should additionally be constrained according to organization/care-team membership.

---

# 17. Screen specification

You already have the correct six-screen structure.

## Screen 1 — Dashboard

Purpose: operational inbox.

Must contain:

```text
Open Threads
Needs Review
Overdue Follow-ups
Recent Evidence
```

Primary table:

```text
Patient
Finding
Status
Owner
Due date
Evidence match
```

Supporting panels:

```text
Why this matters
Recent activity
```

Primary action:

> Open a CareThread.

---

# 18. Screen 2 — Thread Detail

This is the main operational workspace.

Header should show:

```text
Patient
MRN
Thread type
Status
Owner
Due date
Jurisdiction
Priority
```

Main body:

```text
Longitudinal timeline
Evidence citations
Outstanding obligation
Recommended actions
```

Actions:

```text
Assign owner
Request review
Extend deadline
Escalate
Propose closure
```

---

# 19. Screen 3 — Evidence Match Review

This screen explains agent reasoning.

Left:

```text
New evidence
```

Right:

```text
Existing CareThread evidence
```

Match explanation:

```text
Same patient                  ✓
Same finding                  ✓
Follow-up CT referenced       ✓
Timeline consistent           ✓
Match confidence             92%
```

Actions:

```text
Link to Thread
Needs Human Review
Reject Match
```

This screen is particularly valuable for your hackathon demo because it makes the agent's memory usage visible.

---

# 20. Screen 4 — Patient Memory

Purpose:

> View the longitudinal evidence repository underlying CareThread.

Search:

```text
Search within this patient's memory
```

Filters:

```text
Radiology
Notes
Labs
Messages
Images
Discharge
```

Artifact card:

```text
Artifact type
Date
Source
Provider
Summary
Linked CareThreads
```

Do not offer global patient search from this semantic interface in the MVP.

---

# 21. Screen 5 — Clinician Review

A queue of proposed consequential actions.

Metrics:

```text
Proposed Closures
Proposed Escalations
Proposed Extensions
Awaiting Approval
```

Queue fields:

```text
Patient
Thread
Proposed change
Reason
Owner
Requested by
Priority
```

Actions:

```text
Approve
Send Back
Reassign
Reject
```

---

# 22. Screen 6 — History & Provenance

Show an immutable chronological record.

Example:

```text
Mar 12    Radiology report received
Mar 14    Discharge summary received
Mar 18    CareThread proposed
Mar 18    Clinician approved
Mar 18    Coordinator assigned
Apr 02    Reminder generated
May 07    New evidence matched
May 20    Follow-up CT completed
Jun 20    Closure proposed
Jun 20    Clinician closed thread
```

Every event should link to underlying evidence when applicable.

---

# 23. Backend API

A clean API surface could look like this.

```http
POST   /artifacts
GET    /patients/{patient_id}
GET    /patients/{patient_id}/memory
GET    /patients/{patient_id}/threads

GET    /threads
POST   /threads
GET    /threads/{thread_id}
GET    /threads/{thread_id}/timeline
GET    /threads/{thread_id}/evidence

POST   /threads/{thread_id}/assign
POST   /threads/{thread_id}/extend
POST   /threads/{thread_id}/escalate
POST   /threads/{thread_id}/close

POST   /evidence/{artifact_id}/match

GET    /actions
POST   /actions/{action_id}/approve
POST   /actions/{action_id}/reject

GET    /audit/threads/{thread_id}
```

---

# 24. Artifact processing service

Implement adapters around document type rather than one huge prompt.

```python
class ArtifactProcessor:
    def extract_text(...)
    def extract_metadata(...)
    def extract_facts(...)
    def create_chunks(...)
    def create_embeddings(...)
```

Then:

```text
RadiologyProcessor
DischargeProcessor
ProgressNoteProcessor
PatientMessageProcessor
LabProcessor
ImageMetadataProcessor
```

---

# 25. Agent output contract

Never allow free-form agent responses to directly control application state.

Use a structured schema.

```json
{
  "patient_id": "pat_001",
  "thread_id": "thr_001",
  "recommendation": "PROPOSE_CLOSURE",
  "confidence": 0.94,
  "reason": "Follow-up CT has been completed.",
  "evidence": [
    {
      "artifact_id": "art_182",
      "chunk_id": "chk_903",
      "citation": "CT Chest / Impression"
    }
  ],
  "requires_clinician_approval": true
}
```

The backend validates this object before storing the proposed action.

---

# 26. Guardrails

These should exist technically, not only in the UI.

```text
Patient-scoped vector retrieval
Role-based authorization
No unrestricted cohort search
No autonomous diagnosis
No treatment recommendations
No automatic thread closure
No automatic patient outreach
Evidence required for agent assertions
Clinician approval for consequential actions
Complete audit trail
```

The application should display a clear distinction between:

```text
Observed Evidence
Agent Interpretation
Proposed Action
Clinician Decision
```

That separation makes the system much easier to defend technically.

---

# 27. Jurisdiction-aware data model

Each patient and thread should include:

```text
jurisdiction
home_region
organization_id
```

Use regional locality to keep frequently accessed patient state close to its operating jurisdiction.

However, preserve the important limitation from the architecture you described:

> `REGIONAL BY ROW` locality should not be marketed as automatically guaranteeing strict legal residency.

Where strict domiciling is required, deployment-specific CockroachDB placement configuration must be used.

Do not claim that CareThread automatically provides HIPAA, EU, or state-law compliance.

---

# 28. AWS storage design

S3 should contain the original artifacts.

Example hierarchy:

```text
carethread-artifacts/
    synthetic/
        pat_001/
            radiology/
                ct_chest_2026_03_12.pdf
            discharge/
                discharge_2026_03_14.pdf
            notes/
                pcp_2026_04_10.pdf
```

CockroachDB stores pointers such as:

```text
s3://carethread-artifacts/synthetic/pat_001/...
```

Do not store large PDFs/images directly inside database rows.

---

# 29. Demo dataset

Build about **5–10 synthetic patients**, but demonstrate one patient deeply.

Your flagship patient could have:

```text
Jane Doe
61F

March 12:
CT identifies incidental 6 mm pulmonary nodule.

March 14:
Discharge summary does not contain follow-up recommendation.

March 18:
CareThread proposes a follow-up case.

March 18:
Clinician approves and assigns Katherine Lee.

May 07:
New PCP note references pending imaging.

May 20:
Follow-up CT completed.

June 20:
Agent proposes closure.

June 20:
Clinician approves closure.
```

Also include two distracting documents unrelated to the nodule so you can demonstrate that retrieval is selective.

---

# 30. Hackathon demo flow

The strongest live demo would take roughly three minutes.

**0:00–0:30 — Problem**

Show the radiology report.

> “This report contains a follow-up recommendation.”

Show the discharge summary.

> “The recommendation disappears from the patient's discharge workflow.”

**0:30–1:00 — Memory**

Upload both.

Show them entering Patient Memory.

**1:00–1:30 — Agent**

CareThread retrieves both pieces of evidence and proposes:

> Incidental Pulmonary Nodule Follow-up.

Show citations and the reasoning.

**1:30–2:00 — Ownership**

Clinician approves.

Assign a coordinator.

The obligation now survives beyond the encounter.

**2:00–2:30 — Later evidence**

Upload the follow-up CT report.

CareThread retrieves the thread from months earlier and matches the new evidence to it.

**2:30–3:00 — Bounded action**

Agent proposes closure.

Clinician reviews the evidence and approves.

Show History & Provenance.

That demonstrates the central idea:

> **The system remembers obligations, not merely documents.**

---

# 31. Build order

I would implement it in this sequence:

| Phase  | Deliverable                     |
| ------ | ------------------------------- |
| **1**  | CockroachDB schema              |
| **2**  | Synthetic patient dataset       |
| **3**  | S3 artifact ingestion           |
| **4**  | Artifact extraction/chunking    |
| **5**  | Embedding generation            |
| **6**  | Patient-scoped vector retrieval |
| **7**  | CareThread state machine        |
| **8**  | Evidence matching agent         |
| **9**  | Proposed-action/approval model  |
| **10** | Dashboard                       |
| **11** | Thread detail                   |
| **12** | Evidence review                 |
| **13** | Patient memory                  |
| **14** | Clinician review                |
| **15** | Audit timeline                  |
| **16** | End-to-end demo                 |
| **17** | Security + failure handling     |
| **18** | Demo polish                     |

---

# 32. Repository structure

```text
carethread/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── types/
│
├── backend/
│   ├── api/
│   ├── agents/
│   ├── ingestion/
│   ├── retrieval/
│   ├── workflows/
│   ├── models/
│   ├── repositories/
│   └── security/
│
├── infrastructure/
│   ├── template.yaml
│   └── scripts/
│
├── database/
│   ├── migrations/
│   ├── seeds/
│   └── queries/
│
├── demo/
│   ├── patients/
│   ├── reports/
│   └── scenarios/
│
├── tests/
│
├── docs/
│   ├── architecture.md
│   ├── security.md
│   └── demo-script.md
│
└── README.md
```

---

# 33. MVP definition of done

The MVP is complete when you can take a synthetic patient through this entire sequence without manually editing the database:

```text
Artifact uploaded
      ↓
Stored in S3
      ↓
Text extracted
      ↓
Chunks embedded
      ↓
Finding extracted
      ↓
Care gap detected
      ↓
CareThread proposed
      ↓
Clinician approves
      ↓
Owner assigned
      ↓
Later artifact uploaded
      ↓
Patient-scoped retrieval finds old thread
      ↓
Evidence linked
      ↓
Closure proposed
      ↓
Clinician approves
      ↓
Thread closes
      ↓
Full provenance remains visible
```

If that flow works cleanly, you have the actual **soul of CareThread**. The fancy multimodal memory features can expand later; the important innovation is that longitudinal memory becomes a persistent, owned clinical obligation rather than another RAG chat session.

