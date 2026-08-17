from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ProposedAction
from app.schemas import ProposedActionOut, RejectRequest
from app.security.roles import get_current_user, require_approval_role, CurrentUser
from app.workflows.approval_service import approve_action, reject_action

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("", response_model=list[ProposedActionOut])
def list_actions(status: str | None = "PENDING", db: Session = Depends(get_db)):
    stmt = select(ProposedAction)
    if status:
        stmt = stmt.where(ProposedAction.status == status)
    stmt = stmt.order_by(ProposedAction.created_at.desc())
    return db.execute(stmt).scalars().all()


@router.post("/{action_id}/approve", response_model=ProposedActionOut)
def approve(action_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    require_approval_role(user)
    action = db.get(ProposedAction, action_id)
    if not action:
        raise HTTPException(404, "Action not found")
    if action.status != "PENDING":
        raise HTTPException(400, f"Action already {action.status}")
    approve_action(db, action, user.user_id)
    db.commit()
    db.refresh(action)
    return action


@router.post("/{action_id}/reject", response_model=ProposedActionOut)
def reject(action_id: str, payload: RejectRequest, db: Session = Depends(get_db),
           user: CurrentUser = Depends(get_current_user)):
    require_approval_role(user)
    action = db.get(ProposedAction, action_id)
    if not action:
        raise HTTPException(404, "Action not found")
    if action.status != "PENDING":
        raise HTTPException(400, f"Action already {action.status}")
    reject_action(db, action, user.user_id, payload.reason)
    db.commit()
    db.refresh(action)
    return action
