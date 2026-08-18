"""
Patient-scoped chat: a clinician can ask free-form questions about one
patient's own record. Always available (unlike the family chat, which
needs a FamilyGroup) — this is the general "ask about this patient" agent.

Same guardrails as family_chat.py (spec section 26):
  * Grounded only in this ONE patient's artifacts/facts/findings/threads —
    never another patient's data, never outside medical knowledge.
  * Must cite the specific artifact/finding/thread behind each claim.
  * Refuses diagnosis, malignancy assessment, or quantified risk predictions.
  * Every message is persisted (PatientChatMessage) for the audit trail.

Falls back to a deterministic, clearly-labeled summary when
``ai_provider != "bedrock"`` or the Bedrock call fails.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Patient, Artifact, Finding, Fact, CareThread, PatientChatMessage

_SYSTEM = """You are the patient-record assistant inside CareThread, a care-continuity
tool. You answer a clinician's questions about ONE patient using ONLY the
<patient_context> provided below — never outside medical knowledge, never information
about any other patient.

Rules:
- Every factual claim must cite the specific artifact, finding, or thread it comes from
  (e.g. "per the March 12 CT Chest report").
- If the context doesn't contain the answer, say so plainly — do not guess or infer.
- Never diagnose, assess malignancy, or state/estimate a numeric or qualitative risk
  level. If asked, explain that's a clinician's call, not something you provide, and
  describe only the documented facts.
- Keep answers concise and clinician-readable."""


def build_context(db: Session, patient_id: str) -> str:
    patient = db.get(Patient, patient_id)
    artifacts = db.execute(
        select(Artifact).where(Artifact.patient_id == patient_id).order_by(Artifact.document_date.asc())
    ).scalars().all()
    findings = db.execute(select(Finding).where(Finding.patient_id == patient_id)).scalars().all()
    threads = db.execute(select(CareThread).where(CareThread.patient_id == patient_id)).scalars().all()

    lines = [f"Patient: {patient.display_name} (DOB {patient.dob}, MRN {patient.mrn})", "", "Artifacts on file:"]
    for a in artifacts:
        lines.append(f"- {a.document_date} — {a.title} ({a.artifact_type.replace('_', ' ').title()}, {a.source_provider or 'unknown source'})")
        facts = db.execute(select(Fact).where(Fact.artifact_id == a.artifact_id)).scalars().all()
        for f in facts:
            lines.append(f"    fact: {f.fact_type.replace('_', ' ').title()} — {f.fact_text}")
    if not artifacts:
        lines.append("- none")

    lines.append("\nFindings:")
    for f in findings:
        loc = f.anatomical_location.replace("_", " ").title() if f.anatomical_location else "unspecified location"
        lines.append(f"- {f.finding_type.replace('_', ' ').title()} at {loc} — {f.finding_description} (status: {f.status})")
    if not findings:
        lines.append("- none")

    lines.append("\nCareThreads (follow-up obligations):")
    for t in threads:
        lines.append(f"- \"{t.title}\" — type {t.thread_type}, status {t.status}, priority {t.priority}, due {t.due_at or 'n/a'}, owner {t.owner_user_id or 'unassigned'}")
    if not threads:
        lines.append("- none")

    return "\n".join(lines)


def _local_fallback(context: str, question: str) -> str:
    return (
        "AI-assisted chat isn't available right now (CARETHREAD_AI_PROVIDER is not "
        "\"bedrock\", or the Bedrock call failed), so here's the raw data on file for "
        f"this patient instead of an answer to \"{question}\":\n\n{context}"
    )


def answer_patient_question(db: Session, patient_id: str, question: str) -> str:
    context = build_context(db, patient_id)
    if settings.ai_provider != "bedrock":
        return _local_fallback(context, question)
    try:
        from app.ai.bedrock import chat_reply
        return chat_reply(
            system=_SYSTEM,
            user=f"<patient_context>\n{context}\n</patient_context>\n\nQuestion: {question}",
        )
    except Exception:  # noqa: BLE001 — never hard-fail a chat turn
        return _local_fallback(context, question)


def record_message(db: Session, patient_id: str, role: str, content: str) -> PatientChatMessage:
    msg = PatientChatMessage(patient_id=patient_id, role=role, content=content)
    db.add(msg)
    db.flush()
    return msg
