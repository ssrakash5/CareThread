import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ProposedAction(Base):
    __tablename__ = "proposed_actions"

    action_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"act_{uuid.uuid4().hex[:8]}")
    thread_id: Mapped[str] = mapped_column(String, ForeignKey("care_threads.thread_id"), index=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.patient_id"), index=True)
    action_type: Mapped[str] = mapped_column(String)
    proposed_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(String, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source_evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    agent_run_id: Mapped[str] = mapped_column(String, default=lambda: f"run_{uuid.uuid4().hex[:8]}")
    status: Mapped[str] = mapped_column(String, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String, nullable=True)
