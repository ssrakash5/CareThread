from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CareThread, ThreadEvent, ThreadEvidence, ProposedAction
from app.schemas import (
    ThreadOut, ThreadEventOut, ThreadEvidenceOut, ProposedActionOut,
    AssignRequest, ExtendRequest, EscalateRequest,
)
from app.security.roles import get_current_user, require_approval_role, CurrentUser
from app.workflows.approval_service import _log_event
from app.agents.followup_agent import propose_escalations

router = APIRouter(prefix="/threads", tags=["threads"])


@router.post("/check-overdue", response_model=list[ProposedActionOut])
def check_overdue(db: Session = Depends(get_db)):
    """Runs the follow-up agent: scans all open threads for ones past their
    due date and proposes ESCALATE_THREAD (PENDING, requires clinician
    approval like every other agent action)."""
    actions = propose_escalations(db)
    for a in actions:
        db.add(a)
    db.commit()
    for a in actions:
        db.refresh(a)
    return actions


@router.get("", response_model=list[ThreadOut])
def list_threads(status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(CareThread)
    if status:
        stmt = stmt.where(CareThread.status == status)
    stmt = stmt.order_by(CareThread.updated_at.desc())
    return db.execute(stmt).scalars().all()


@router.get("/{thread_id}", response_model=ThreadOut)
def get_thread(thread_id: str, db: Session = Depends(get_db)):
    thread = db.get(CareThread, thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")
    return thread


@router.get("/{thread_id}/timeline", response_model=list[ThreadEventOut])
def get_timeline(thread_id: str, db: Session = Depends(get_db)):
    stmt = select(ThreadEvent).where(ThreadEvent.thread_id == thread_id).order_by(ThreadEvent.created_at.asc())
    return db.execute(stmt).scalars().all()


@router.get("/{thread_id}/evidence", response_model=list[ThreadEvidenceOut])
def get_evidence(thread_id: str, db: Session = Depends(get_db)):
    stmt = select(ThreadEvidence).where(ThreadEvidence.thread_id == thread_id).order_by(ThreadEvidence.linked_at.asc())
    return db.execute(stmt).scalars().all()


@router.post("/{thread_id}/assign", response_model=ThreadOut)
def assign_owner(thread_id: str, payload: AssignRequest, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(get_current_user)):
    thread = db.get(CareThread, thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")
    thread.owner_user_id = payload.owner_user_id
    _log_event(db, thread_id, thread.patient_id, "OWNER_ASSIGNED", user.user_id, thread.status, thread.status,
               {"owner_user_id": payload.owner_user_id})
    db.commit()
    db.refresh(thread)
    return thread


@router.post("/{thread_id}/extend", response_model=ThreadOut)
def extend_due_date(thread_id: str, payload: ExtendRequest, db: Session = Depends(get_db),
                     user: CurrentUser = Depends(get_current_user)):
    require_approval_role(user)
    thread = db.get(CareThread, thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")
    thread.due_at = payload.new_due_at
    _log_event(db, thread_id, thread.patient_id, "DEADLINE_EXTENDED", user.user_id, thread.status, thread.status,
               {"new_due_at": str(payload.new_due_at), "reason": payload.reason})
    db.commit()
    db.refresh(thread)
    return thread


@router.post("/{thread_id}/escalate", response_model=ThreadOut)
def escalate_thread(thread_id: str, payload: EscalateRequest, db: Session = Depends(get_db),
                     user: CurrentUser = Depends(get_current_user)):
    require_approval_role(user)
    from app.workflows.thread_state_machine import validate_transition
    thread = db.get(CareThread, thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")
    validate_transition(thread.status, "ESCALATED")
    prev = thread.status
    thread.status = "ESCALATED"
    thread.priority = "URGENT"
    _log_event(db, thread_id, thread.patient_id, "ESCALATION_APPROVED", user.user_id, prev, "ESCALATED",
               {"reason": payload.reason})
    db.commit()
    db.refresh(thread)
    return thread
