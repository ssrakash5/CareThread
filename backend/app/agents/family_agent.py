"""
Family / hereditary-risk agent.

The one sanctioned cross-patient read in CareThread: matching_agent.py is
strictly patient-scoped (spec section 26), but detecting a hereditary
pattern is inherently cross-patient within a single consented family unit,
so this module queries across the members of one FamilyGroup only — never
across unrelated patients.

Follows the same contract as action_agent.py: returns unpersisted
(CareThread, ProposedAction) pairs for the caller to persist. Never writes
state directly and never diagnoses; it only flags a pattern (>=2 blood
relatives sharing the same finding_type + anatomical_location) for
clinician review. Uses action_type="OPEN_THREAD" (thread_type carries the
"HEREDITARY_RISK_REVIEW" distinction) so the existing approval_service.py
PROPOSED->OPEN->IN_PROGRESS handling applies unchanged.
"""
from collections import defaultdict
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Patient, Finding, CareThread, ProposedAction

MIN_RELATIVES_FOR_FLAG = 2


def analyze_family(db: Session, family_id: str) -> List[Tuple[CareThread, ProposedAction]]:
    members = db.execute(select(Patient).where(Patient.family_id == family_id)).scalars().all()
    if len(members) < MIN_RELATIVES_FOR_FLAG:
        return []

    by_pattern: dict[tuple[str, str], list[tuple[Patient, Finding]]] = defaultdict(list)
    for patient in members:
        findings = db.execute(select(Finding).where(Finding.patient_id == patient.patient_id)).scalars().all()
        for f in findings:
            if not f.finding_type:
                continue
            by_pattern[(f.finding_type, f.anatomical_location)].append((patient, f))

    results: List[Tuple[CareThread, ProposedAction]] = []
    for (finding_type, location), entries in by_pattern.items():
        distinct_patient_ids = {p.patient_id for p, _ in entries}
        if len(distinct_patient_ids) < MIN_RELATIVES_FOR_FLAG:
            continue

        pretty_type = finding_type.replace("_", " ").title()
        pretty_loc = location.replace("_", " ").title() if location else "an unspecified location"
        names = ", ".join(sorted({p.display_name for p, _ in entries}))
        reason = (
            f"{len(distinct_patient_ids)} family members ({names}) each have a documented "
            f"{pretty_type} finding at {pretty_loc}. This shared pattern across blood "
            f"relatives may warrant hereditary-risk review; it is not a diagnosis."
        )

        anchor_patient, anchor_finding = entries[0]
        thread = CareThread(
            patient_id=anchor_patient.patient_id,
            thread_type="HEREDITARY_RISK_REVIEW",
            title=f"Possible Hereditary {pretty_type} Pattern",
            finding_id=anchor_finding.finding_id,
            status="PROPOSED",
        )
        action = ProposedAction(
            thread_id="",  # filled by the caller once the thread row is persisted
            patient_id=anchor_patient.patient_id,
            action_type="OPEN_THREAD",
            proposed_payload={
                "thread_type": "HEREDITARY_RISK_REVIEW",
                "title": thread.title,
                "family_id": family_id,
                "related_patient_ids": sorted(distinct_patient_ids),
                "priority": "ROUTINE",
            },
            reason=reason,
            confidence=0.7,
            source_evidence={"finding_ids": [f.finding_id for _, f in entries]},
        )
        results.append((thread, action))

    return results
