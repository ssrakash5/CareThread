import uuid
from datetime import datetime, date

from sqlalchemy import String, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CareThread(Base):
    __tablename__ = "care_threads"

    thread_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"thr_{uuid.uuid4().hex[:8]}")
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.patient_id"), index=True)
    thread_type: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    finding_id: Mapped[str] = mapped_column(String, ForeignKey("findings.finding_id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="PROPOSED")
    priority: Mapped[str] = mapped_column(String, default="ROUTINE")
    owner_user_id: Mapped[str] = mapped_column(String, nullable=True)
    jurisdiction: Mapped[str] = mapped_column(String, default="US-GENERIC")
    home_region: Mapped[str] = mapped_column(String, default="us-demo")
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    due_at: Mapped[date] = mapped_column(Date, nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    closure_reason: Mapped[str] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String, default="care_agent")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
