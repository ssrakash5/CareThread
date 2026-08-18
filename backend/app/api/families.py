from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import FamilyGroup, FamilyRelationship, Patient, ProposedAction, FamilyChatMessage
from app.schemas import (
    FamilyOut, FamilyMemberOut, FamilyRelationshipOut, ProposedActionOut,
    FamilyChatMessageOut, FamilyChatRequest,
)
from app.agents.family_agent import analyze_family
from app.ai.family_chat import answer_family_question, record_message

router = APIRouter(prefix="/families", tags=["families"])


def build_family_out(db: Session, group: FamilyGroup) -> FamilyOut:
    members = db.execute(select(Patient).where(Patient.family_id == group.family_id)).scalars().all()
    relationships = db.execute(
        select(FamilyRelationship).where(FamilyRelationship.family_id == group.family_id)
    ).scalars().all()
    return FamilyOut(
        family_id=group.family_id,
        family_name=group.family_name,
        members=[FamilyMemberOut.model_validate(m) for m in members],
        relationships=[FamilyRelationshipOut.model_validate(r) for r in relationships],
    )


@router.get("/{family_id}", response_model=FamilyOut)
def get_family(family_id: str, db: Session = Depends(get_db)):
    group = db.get(FamilyGroup, family_id)
    if not group:
        raise HTTPException(404, "Family group not found")
    return build_family_out(db, group)


@router.post("/{family_id}/analyze", response_model=list[ProposedActionOut])
def analyze(family_id: str, db: Session = Depends(get_db)):
    group = db.get(FamilyGroup, family_id)
    if not group:
        raise HTTPException(404, "Family group not found")

    pairs = analyze_family(db, family_id)
    actions: list[ProposedAction] = []
    for thread, action in pairs:
        db.add(thread)
        db.flush()
        action.thread_id = thread.thread_id
        db.add(action)
        actions.append(action)
    db.commit()
    for a in actions:
        db.refresh(a)
    return actions


@router.get("/{family_id}/chat", response_model=list[FamilyChatMessageOut])
def get_chat_history(family_id: str, db: Session = Depends(get_db)):
    if not db.get(FamilyGroup, family_id):
        raise HTTPException(404, "Family group not found")
    stmt = (
        select(FamilyChatMessage)
        .where(FamilyChatMessage.family_id == family_id)
        .order_by(FamilyChatMessage.created_at.asc())
    )
    return db.execute(stmt).scalars().all()


@router.post("/{family_id}/chat", response_model=FamilyChatMessageOut)
def post_chat_message(family_id: str, payload: FamilyChatRequest, db: Session = Depends(get_db)):
    if not db.get(FamilyGroup, family_id):
        raise HTTPException(404, "Family group not found")
    record_message(db, family_id, "user", payload.question)
    answer = answer_family_question(db, family_id, payload.question)
    assistant_msg = record_message(db, family_id, "assistant", answer)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg
