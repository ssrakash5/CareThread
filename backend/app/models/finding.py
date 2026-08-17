import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Finding(Base):
    __tablename__ = "findings"

    finding_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"find_{uuid.uuid4().hex[:8]}")
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.patient_id"), index=True)
    finding_type: Mapped[str] = mapped_column(String)
    anatomical_location: Mapped[str] = mapped_column(String, default="")
    finding_description: Mapped[str] = mapped_column(Text)
    source_artifact_id: Mapped[str] = mapped_column(String, ForeignKey("artifacts.artifact_id"))
    source_chunk_id: Mapped[str] = mapped_column(String, ForeignKey("artifact_chunks.chunk_id"))
    first_observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    latest_observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
