"""
Family hereditary-history chat: a clinician can ask free-form questions
about one family cluster, with that family's documented data as the only
context. This is the one place in CareThread that behaves like a chatbot —
scoped narrowly (spec section 26 guardrails still apply):

  * Grounded only in this family's stored relationships/findings/threads —
    never invents facts, never reasons from outside knowledge.
  * Must cite which patient/finding backs each claim it makes.
  * Refuses diagnosis, malignancy assessment, or quantified risk predictions
    ("what are the odds...") — those are exactly what the product spec says
    CareThread does not do.
  * Every message (both sides) is persisted (FamilyChatMessage) for the same
    audit-trail reason the rest of the app logs ThreadEvents.

Falls back to a deterministic, clearly-labeled summary when
``ai_provider != "bedrock"`` or the Bedrock call fails — never silently
answers as if it were unavailable.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Patient, Finding, FamilyRelationship, CareThread, FamilyChatMessage

_SYSTEM = """You are the family-history assistant inside CareThread, a care-continuity
tool. You answer a clinician's questions about ONE family cluster using ONLY the
<family_context> provided below — never outside medical knowledge, never information
about other patients or families.

Rules:
- Every factual claim must cite the specific patient and finding/thread it comes from
  (e.g. "Susan Doe has a documented 5mm right-upper-lobe nodule").
- If the context doesn't contain the answer, say so plainly — do not guess or infer.
- Never diagnose, assess malignancy, or state/estimate a numeric or qualitative risk
  level ("high risk", "70% chance", etc.). If asked, explain that risk assessment is a
  clinician's call, not something you provide, and describe only the documented pattern.
- Keep answers concise and clinician-readable."""


def _build_context(db: Session, family_id: str) -> str:
    members = db.execute(select(Patient).where(Patient.family_id == family_id)).scalars().all()
    relationships = db.execute(
        select(FamilyRelationship).where(FamilyRelationship.family_id == family_id)
    ).scalars().all()
    threads = db.execute(
        select(CareThread).where(CareThread.thread_type == "HEREDITARY_RISK_REVIEW")
    ).scalars().all()
    member_ids = {m.patient_id for m in members}

    lines = ["Family members:"]
    for m in members:
        findings = db.execute(select(Finding).where(Finding.patient_id == m.patient_id)).scalars().all()
        lines.append(f"- {m.display_name} (patient_id {m.patient_id}, DOB {m.dob})")
        for f in findings:
            loc = f.anatomical_location.replace("_", " ").title() if f.anatomical_location else "unspecified location"
            lines.append(f"    finding: {f.finding_type.replace('_', ' ').title()} at {loc} — {f.finding_description}")
        if not findings:
            lines.append("    no findings on file")

    lines.append("\nRelationships:")
    for r in relationships:
        who = next((m.display_name for m in members if m.patient_id == r.patient_id), r.patient_id)
        related = next((m.display_name for m in members if m.patient_id == r.related_patient_id), r.related_patient_id)
        lines.append(f"- {who} is {related}'s {r.relationship_type.lower()}")

    family_threads = [t for t in threads if t.patient_id in member_ids]
    lines.append("\nHereditary-risk review threads for this family:")
    if family_threads:
        for t in family_threads:
            lines.append(f"- \"{t.title}\" — status {t.status} (anchored on patient {t.patient_id})")
    else:
        lines.append("- none")

    return "\n".join(lines)


def _local_fallback(context: str, question: str) -> str:
    return (
        "AI-assisted chat isn't available right now (CARETHREAD_AI_PROVIDER is not "
        "\"bedrock\", or the Bedrock call failed), so here's the raw data on file for "
        f"this family instead of an answer to \"{question}\":\n\n{context}"
    )


def answer_family_question(db: Session, family_id: str, question: str) -> str:
    context = _build_context(db, family_id)
    if settings.ai_provider != "bedrock":
        return _local_fallback(context, question)
    try:
        from app.ai.bedrock import chat_reply
        return chat_reply(
            system=_SYSTEM,
            user=f"<family_context>\n{context}\n</family_context>\n\nQuestion: {question}",
        )
    except Exception:  # noqa: BLE001 — never hard-fail a chat turn
        return _local_fallback(context, question)


def record_message(db: Session, family_id: str, role: str, content: str) -> FamilyChatMessage:
    msg = FamilyChatMessage(family_id=family_id, role=role, content=content)
    db.add(msg)
    db.flush()
    return msg
