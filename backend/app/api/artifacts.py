from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Patient
from app.schemas import ArtifactIngest, IngestResult
from app.ingestion.pipeline import ingest_artifact

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.post("/{patient_id}", response_model=IngestResult)
def ingest(patient_id: str, payload: ArtifactIngest, db: Session = Depends(get_db)):
    if not db.get(Patient, patient_id):
        raise HTTPException(404, "Patient not found")
    result = ingest_artifact(
        db, patient_id,
        artifact_type=payload.artifact_type,
        title=payload.title,
        text=payload.text,
        document_date=payload.document_date,
        source_provider=payload.source_provider,
    )
    db.commit()
    return result
