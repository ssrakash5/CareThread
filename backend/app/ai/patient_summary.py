"""
One or two-sentence clinical summary for the top of a patient's page —
same grounding/guardrails as patient_chat.py (spec section 26): built only
from this patient's own documented data, cites specifics, never diagnoses
or assesses risk. Not persisted — cheap enough to regenerate on demand,
and it should always reflect the current record.
"""
from app.config import settings
from app.ai.patient_chat import build_context

_SYSTEM = """You write a one-to-two sentence clinical summary of a patient's current
CareThread status, for a clinician glancing at their record. Use ONLY the
<patient_context> provided. State: the most clinically significant active finding or
obligation (if any) and its status, using specifics from the context (dates, findings,
thread status). If there's nothing notable, say so plainly. Never diagnose, assess
malignancy, or state a risk level. No preamble — output only the summary sentence(s)."""


def _local_summary(db, patient_id: str) -> str:
    from sqlalchemy import select
    from app.models import Artifact, CareThread

    artifact_count = len(db.execute(select(Artifact).where(Artifact.patient_id == patient_id)).scalars().all())
    open_threads = [
        t for t in db.execute(select(CareThread).where(CareThread.patient_id == patient_id)).scalars().all()
        if t.status not in ("CLOSED", "REJECTED")
    ]
    if not open_threads:
        return f"{artifact_count} artifact(s) on file; no open follow-up obligations."
    lead = open_threads[0]
    extra = f" (+{len(open_threads) - 1} more)" if len(open_threads) > 1 else ""
    return f"{artifact_count} artifact(s) on file. Open: \"{lead.title}\" — {lead.status.replace('_', ' ').lower()}{extra}."


def generate_patient_summary(db, patient_id: str) -> str:
    if settings.ai_provider != "bedrock":
        return _local_summary(db, patient_id)
    try:
        from app.ai.bedrock import chat_reply
        context = build_context(db, patient_id)
        return chat_reply(system=_SYSTEM, user=f"<patient_context>\n{context}\n</patient_context>", max_tokens=200)
    except Exception:  # noqa: BLE001
        return _local_summary(db, patient_id)
