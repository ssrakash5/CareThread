from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Patient, Artifact, CareThread
from app.schemas import PatientOut, PatientCreate, ArtifactOut, ThreadOut

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
