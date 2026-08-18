from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Patient
from app.schemas import ArtifactIngest, IngestResult
from app.ingestion.pipeline import ingest_artifact
from app.ingestion.pdf_utils import extract_text_from_pdf

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


@router.post("/{patient_id}/upload", response_model=IngestResult)
def upload(
    patient_id: str,
    file: UploadFile = File(...),
    artifact_type: str = Form(...),
    title: str = Form(...),
    document_date: str = Form(...),
    source_provider: str = Form(""),
    caption: str = Form(""),
    db: Session = Depends(get_db),
):
    """Real file upload — PDFs get text-extracted through the same pipeline a
    pasted report would use; images are stored + captioned only (spec section
    3: reference artifacts, never auto-interpreted, so a caption is required)."""
    if not db.get(Patient, patient_id):
        raise HTTPException(404, "Patient not found")

    data = file.file.read()
    ext = Path(file.filename or "").suffix.lstrip(".").lower() or "bin"
    content_type = file.content_type or ""

    if content_type == "application/pdf" or ext == "pdf":
        text = extract_text_from_pdf(data)
        mime_type = "application/pdf"
        if not text.strip():
            raise HTTPException(400, "Could not extract any text from that PDF")
    elif content_type.startswith("image/") or ext in {"png", "jpg", "jpeg"}:
        if not caption.strip():
            raise HTTPException(400, "Images require a caption — CareThread never auto-interprets pixel content")
        text = caption
        mime_type = content_type or f"image/{ext}"
        artifact_type = "IMAGE"
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(400, "Unsupported file type — upload a PDF, an image, or a plain-text file")
        mime_type = content_type or "text/plain"

    from datetime import date as date_cls
    result = ingest_artifact(
        db, patient_id,
        artifact_type=artifact_type,
        title=title,
        text=text,
        document_date=date_cls.fromisoformat(document_date),
        source_provider=source_provider,
        raw_bytes=data,
        raw_ext=ext,
        mime_type=mime_type,
    )
    db.commit()
    return result
