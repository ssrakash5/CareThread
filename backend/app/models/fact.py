import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Fact(Base):
    __tablename__ = "facts"

    fact_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"fact_{uuid.uuid4().hex[:8]}")
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.patient_id"), index=True)
    artifact_id: Mapped[str] = mapped_column(String, ForeignKey("artifacts.artifact_id"))
    chunk_id: Mapped[str] = mapped_column(String, ForeignKey("artifact_chunks.chunk_id"))
    fact_type: Mapped[str] = mapped_column(String)
    fact_text: Mapped[str] = mapped_column(Text)
    normalized_value: Mapped[str] = mapped_column(String, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
