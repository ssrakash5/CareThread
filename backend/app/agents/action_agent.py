"""
Care agent action proposals (spec sections 13, 14, 25). The agent only ever
produces PENDING ProposedAction rows through this small action interface —
it never writes to care_threads/thread_evidence directly. The workflow
service (approval_service.py) is what executes state.
"""
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ProposedAction, Finding, Artifact
from app.ingestion.extractors import ExtractedFact


def propose_thread(
    db: Session,
    patient_id: str,
    finding: Finding,
    followup_fact: Optional[ExtractedFact],
    source_artifact: Artifact,
) -> ProposedAction:
    interval_months = 9
    if followup_fact and followup_fact.normalized_value:
        digits = "".join(c for c in followup_fact.normalized_value if c.isdigit() or c in "-")
        nums = [int(n) for n in digits.replace("to", "-").split("-") if n.isdigit()]
        if nums:
            interval_months = sum(nums) // len(nums)

    due_at = date.today() + timedelta(days=interval_months * 30)
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


def propose_closure(db: Session, thread_id: str, patient_id: str, artifact_id: str, chunk_id: str, reason: str) -> ProposedAction:
    return ProposedAction(
        thread_id=thread_id,
        patient_id=patient_id,
        action_type="CLOSE_THREAD",
        proposed_payload={"closure_reason": reason},
        reason=reason,
        confidence=0.9,
        source_evidence={"artifact_id": artifact_id, "chunk_id": chunk_id},
    )
