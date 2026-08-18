from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Patient, Artifact, CareThread, FamilyGroup, PatientChatMessage
from app.schemas import (
    PatientOut, PatientCreate, ArtifactOut, ThreadOut, FamilyOut,
    PatientChatMessageOut, PatientChatRequest,
)
from app.api.families import build_family_out
from app.ai.patient_chat import answer_patient_question, record_message

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(db: Session = Depends(get_db)):
    return db.execute(select(Patient)).scalars().all()


@router.post("", response_model=PatientOut)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    patient = Patient(**payload.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    return patient


@router.get("/{patient_id}/memory", response_model=list[ArtifactOut])
def get_patient_memory(patient_id: str, artifact_type: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Artifact).where(Artifact.patient_id == patient_id)
    if artifact_type:
        stmt = stmt.where(Artifact.artifact_type == artifact_type)
    stmt = stmt.order_by(Artifact.document_date.desc())
    return db.execute(stmt).scalars().all()


@router.get("/{patient_id}/threads", response_model=list[ThreadOut])
def get_patient_threads(patient_id: str, db: Session = Depends(get_db)):
    stmt = select(CareThread).where(CareThread.patient_id == patient_id).order_by(CareThread.updated_at.desc())
    return db.execute(stmt).scalars().all()


@router.get("/{patient_id}/family", response_model=FamilyOut)
def get_patient_family(patient_id: str, db: Session = Depends(get_db)):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    if not patient.family_id:
        raise HTTPException(404, "Patient is not part of a family group")
    group = db.get(FamilyGroup, patient.family_id)
    return build_family_out(db, group)


@router.get("/{patient_id}/chat", response_model=list[PatientChatMessageOut])
def get_patient_chat(patient_id: str, db: Session = Depends(get_db)):
    if not db.get(Patient, patient_id):
        raise HTTPException(404, "Patient not found")
    stmt = (
        select(PatientChatMessage)
        .where(PatientChatMessage.patient_id == patient_id)
        .order_by(PatientChatMessage.created_at.asc())
    )
    return db.execute(stmt).scalars().all()


@router.post("/{patient_id}/chat", response_model=PatientChatMessageOut)
def post_patient_chat(patient_id: str, payload: PatientChatRequest, db: Session = Depends(get_db)):
    if not db.get(Patient, patient_id):
        raise HTTPException(404, "Patient not found")
    record_message(db, patient_id, "user", payload.question)
    answer = answer_patient_question(db, patient_id, payload.question)
    assistant_msg = record_message(db, patient_id, "assistant", answer)
    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg
