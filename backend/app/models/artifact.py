import uuid
from datetime import datetime, date

from sqlalchemy import String, Date, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.db import Base
from app.config import settings


class Artifact(Base):
    __tablename__ = "artifacts"

    artifact_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"art_{uuid.uuid4().hex[:8]}")
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.patient_id"), index=True)
    artifact_type: Mapped[str] = mapped_column(String)
    source_system: Mapped[str] = mapped_column(String, default="demo-upload")
    source_provider: Mapped[str] = mapped_column(String, default="")
    document_date: Mapped[date] = mapped_column(Date)
    s3_uri: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String, default="text/plain")
    title: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="PROCESSED")
    jurisdiction: Mapped[str] = mapped_column(String, default="US-GENERIC")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ArtifactChunk(Base):
    __tablename__ = "artifact_chunks"

    chunk_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"chk_{uuid.uuid4().hex[:8]}")
    artifact_id: Mapped[str] = mapped_column(String, ForeignKey("artifacts.artifact_id"), index=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.patient_id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(Vector(settings.embedding_dim))
    section_name: Mapped[str] = mapped_column(String, default="")
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
