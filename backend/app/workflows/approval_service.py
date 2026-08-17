"""
Executes an approved/rejected ProposedAction. This is the only place that
mutates care_threads state, per the guardrail that the agent cannot write
to application state directly (spec sections 13, 26).
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import ProposedAction, CareThread, ThreadEvent, ThreadEvidence
from app.workflows.thread_state_machine import validate_transition


def _log_event(db: Session, thread_id: str, patient_id: str, event_type: str,
                actor_id: str, previous_state: str | None, new_state: str | None,
                metadata: dict | None = None):
    db.add(ThreadEvent(
        thread_id=thread_id,
        patient_id=patient_id,
        event_type=event_type,
        actor_type="clinician" if actor_id != "care_agent" else "care_agent",
        actor_id=actor_id,
        previous_state=previous_state,
        new_state=new_state,
        event_metadata=metadata or {},
    ))


def approve_action(db: Session, action: ProposedAction, reviewer_id: str) -> ProposedAction:
    action.status = "APPROVED"
    action.reviewed_at = datetime.utcnow()
    action.reviewed_by = reviewer_id

    if action.action_type == "OPEN_THREAD":
        thread = db.get(CareThread, action.thread_id)
        validate_transition(thread.status, "OPEN")
        prev = thread.status
        thread.status = "OPEN"
        thread.opened_at = datetime.utcnow()
        _log_event(db, thread.thread_id, thread.patient_id, "THREAD_OPENED", reviewer_id, prev, "OPEN")
        thread.status = "IN_PROGRESS"
        _log_event(db, thread.thread_id, thread.patient_id, "THREAD_IN_PROGRESS", "care_agent", "OPEN", "IN_PROGRESS")

    elif action.action_type == "LINK_EVIDENCE":
        thread = db.get(CareThread, action.thread_id)
        ev = ThreadEvidence(
            thread_id=action.thread_id,
            artifact_id=action.source_evidence.get("artifact_id"),
            chunk_id=action.source_evidence.get("chunk_id"),
            relationship_type=action.proposed_payload.get("relationship_type", "STATUS_UPDATE"),
            match_score=action.confidence,
            match_reason=action.reason,
            linked_by=reviewer_id,
            approval_status="APPROVED",
        )
        db.add(ev)
        _log_event(db, thread.thread_id, thread.patient_id, "EVIDENCE_LINKED", reviewer_id, thread.status, thread.status,
                   {"artifact_id": ev.artifact_id})

    elif action.action_type == "ASSIGN_OWNER":
        thread = db.get(CareThread, action.thread_id)
        thread.owner_user_id = action.proposed_payload.get("owner_user_id")
        _log_event(db, thread.thread_id, thread.patient_id, "OWNER_ASSIGNED", reviewer_id, thread.status, thread.status,
                   {"owner_user_id": thread.owner_user_id})

    elif action.action_type == "EXTEND_DUE_DATE":
        thread = db.get(CareThread, action.thread_id)
        thread.due_at = action.proposed_payload.get("new_due_at")
        _log_event(db, thread.thread_id, thread.patient_id, "DEADLINE_EXTENDED", reviewer_id, thread.status, thread.status,
                   {"new_due_at": str(thread.due_at)})

    elif action.action_type == "ESCALATE_THREAD":
        thread = db.get(CareThread, action.thread_id)
        validate_transition(thread.status, "ESCALATED")
        prev = thread.status
        thread.status = "ESCALATED"
        thread.priority = "URGENT"
        _log_event(db, thread.thread_id, thread.patient_id, "ESCALATION_APPROVED", reviewer_id, prev, "ESCALATED")

    elif action.action_type == "CLOSE_THREAD":
        thread = db.get(CareThread, action.thread_id)
        validate_transition(thread.status, "CLOSURE_PROPOSED")
        db.flush()
        prev = thread.status
        thread.status = "CLOSURE_PROPOSED"
        _log_event(db, thread.thread_id, thread.patient_id, "CLOSURE_PROPOSED", "care_agent", prev, "CLOSURE_PROPOSED")
        validate_transition("CLOSURE_PROPOSED", "CLOSED")
        thread.status = "CLOSED"
        thread.closed_at = datetime.utcnow()
        thread.closure_reason = action.proposed_payload.get("closure_reason", action.reason)
        _log_event(db, thread.thread_id, thread.patient_id, "THREAD_CLOSED", reviewer_id, "CLOSURE_PROPOSED", "CLOSED",
                   {"closure_reason": thread.closure_reason})

    elif action.action_type == "REOPEN_THREAD":
        thread = db.get(CareThread, action.thread_id)
        validate_transition(thread.status, "OPEN")
        prev = thread.status
        thread.status = "OPEN"
        thread.closed_at = None
        _log_event(db, thread.thread_id, thread.patient_id, "THREAD_REOPENED", reviewer_id, prev, "OPEN")

    db.add(action)
    return action


def reject_action(db: Session, action: ProposedAction, reviewer_id: str, reason: str = "") -> ProposedAction:
    action.status = "REJECTED"
    action.reviewed_at = datetime.utcnow()
    action.reviewed_by = reviewer_id

    if action.action_type == "OPEN_THREAD":
        thread = db.get(CareThread, action.thread_id)
        validate_transition(thread.status, "REJECTED")
        prev = thread.status
        thread.status = "REJECTED"
        _log_event(db, thread.thread_id, thread.patient_id, "THREAD_REJECTED", reviewer_id, prev, "REJECTED",
                   {"reason": reason})
    else:
        thread = db.get(CareThread, action.thread_id)
        if thread:
            _log_event(db, thread.thread_id, thread.patient_id, f"{action.action_type}_REJECTED", reviewer_id,
                       thread.status, thread.status, {"reason": reason})

    db.add(action)
    return action
