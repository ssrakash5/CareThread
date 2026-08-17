import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ThreadEvent(Base):
    __tablename__ = "thread_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    thread_id: Mapped[str] = mapped_column(String, ForeignKey("care_threads.thread_id"), index=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.patient_id"), index=True)
    event_type: Mapped[str] = mapped_column(String)
    actor_type: Mapped[str] = mapped_column(String, default="care_agent")
    actor_id: Mapped[str] = mapped_column(String, default="care_agent")
    previous_state: Mapped[str] = mapped_column(String, nullable=True)
    new_state: Mapped[str] = mapped_column(String, nullable=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
