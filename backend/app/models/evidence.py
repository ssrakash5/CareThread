import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ThreadEvidence(Base):
    __tablename__ = "thread_evidence"

    thread_evidence_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"tev_{uuid.uuid4().hex[:8]}")
    thread_id: Mapped[str] = mapped_column(String, ForeignKey("care_threads.thread_id"), index=True)
    artifact_id: Mapped[str] = mapped_column(String, ForeignKey("artifacts.artifact_id"))
    chunk_id: Mapped[str] = mapped_column(String, ForeignKey("artifact_chunks.chunk_id"), nullable=True)
    relationship_type: Mapped[str] = mapped_column(String)
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    match_reason: Mapped[str] = mapped_column(String, default="")
    linked_by: Mapped[str] = mapped_column(String, default="care_agent")
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approval_status: Mapped[str] = mapped_column(String, default="PENDING")
