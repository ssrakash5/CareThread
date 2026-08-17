"""
Care agent action proposals (spec sections 13, 14, 25). The agent only ever
produces PENDING ProposedAction rows through this small action interface —
it never writes to care_threads/thread_evidence directly. The workflow
service (approval_service.py) is what executes state.
"""
import re
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ProposedAction, Finding, Artifact
from app.ingestion.extractors import ExtractedFact

_INTERVAL_RE = re.compile(r"(\d+)(?:\s*(?:-|to)\s*(\d+))?\s*(day|week|month|year)s?", re.IGNORECASE)
_UNIT_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}


def _interval_days(normalized_value: str, default_days: int = 270) -> int:
    """'6-12months' -> 270, '4weeks' -> 28, '6 months' -> 180. Ranges use the
    midpoint. Falls back to ~9 months when no interval is parseable."""
    m = _INTERVAL_RE.search(normalized_value or "")
    if not m:
        return default_days
    lo = int(m.group(1))
    hi = int(m.group(2)) if m.group(2) else lo
    return max(1, ((lo + hi) // 2) * _UNIT_DAYS[m.group(3).lower()])


def propose_thread(
    db: Session,
    patient_id: str,
    finding: Finding,
    followup_fact: Optional[ExtractedFact],
    source_artifact: Artifact,
) -> ProposedAction:
    interval_days = _interval_days(followup_fact.normalized_value if followup_fact else "")
    due_at = date.today() + timedelta(days=interval_days)
    title = f"Incidental {finding.finding_type.replace('_', ' ').title()} Follow-up"

    action = ProposedAction(
        thread_id="",  # filled by caller after thread row is created in PROPOSED state
        patient_id=patient_id,
        action_type="OPEN_THREAD",
        proposed_payload={
            "thread_type": "INCIDENTAL_PULMONARY_FOLLOWUP" if finding.finding_type == "PULMONARY_NODULE" else "INCIDENTAL_FOLLOWUP",
            "title": title,
            "finding_id": finding.finding_id,
            "due_at": due_at.isoformat(),
            "priority": "ROUTINE",
        },
        reason=(
            f"{finding.finding_description} was identified with a documented follow-up "
            f"recommendation that does not appear to have been carried into subsequent care."
        ),
        confidence=0.88,
        source_evidence={"artifact_id": source_artifact.artifact_id, "chunk_id": finding.source_chunk_id},
    )
    return action


def propose_closure(db: Session, thread_id: str, patient_id: str, artifact_id: str, chunk_id: Optional[str], reason: str) -> ProposedAction:
    return ProposedAction(
        thread_id=thread_id,
        patient_id=patient_id,
        action_type="CLOSE_THREAD",
        proposed_payload={"closure_reason": reason},
        reason=reason,
        confidence=0.9,
        source_evidence={"artifact_id": artifact_id, "chunk_id": chunk_id},
    )
