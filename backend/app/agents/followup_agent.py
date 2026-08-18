"""
Follow-up / overdue-obligation agent (spec sections 10, 13). Scans all open
threads for ones past their due date and proposes escalation — never
transitions state itself; approve_action()'s ESCALATE_THREAD branch is what
steps the thread through AWAITING_EVIDENCE -> OVERDUE -> ESCALATED once a
clinician approves.
"""
from datetime import date
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CareThread, ProposedAction

OPEN_NONTERMINAL = {"OPEN", "IN_PROGRESS", "AWAITING_EVIDENCE", "OVERDUE"}


def find_overdue_threads(db: Session) -> List[CareThread]:
    threads = db.execute(select(CareThread).where(CareThread.status.in_(OPEN_NONTERMINAL))).scalars().all()
    today = date.today()
    return [t for t in threads if t.due_at and t.due_at < today]


def propose_escalations(db: Session) -> List[ProposedAction]:
    """Unpersisted ProposedAction rows for every overdue thread that doesn't
    already have a pending ESCALATE_THREAD action."""
    already_pending = {
        a.thread_id for a in db.execute(
            select(ProposedAction).where(
                ProposedAction.action_type == "ESCALATE_THREAD",
                ProposedAction.status == "PENDING",
            )
        ).scalars().all()
    }
    today = date.today()
    actions = []
    for t in find_overdue_threads(db):
        if t.thread_id in already_pending:
            continue
        days_overdue = (today - t.due_at).days
        actions.append(ProposedAction(
            thread_id=t.thread_id,
            patient_id=t.patient_id,
            action_type="ESCALATE_THREAD",
            proposed_payload={"reason": f"overdue_{days_overdue}_days"},
            reason=f"\"{t.title}\" is {days_overdue} day(s) past its due date ({t.due_at}) with no closing evidence on file.",
            confidence=round(min(0.6 + days_overdue / 60, 0.95), 2),
            source_evidence={},
        ))
    return actions
