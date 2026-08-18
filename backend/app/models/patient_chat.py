import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PatientChatMessage(Base):
    """Persisted for the same audit-trail reason as FamilyChatMessage
    (spec section 15) — always available per patient, independent of
    whether that patient belongs to a family group."""
    __tablename__ = "patient_chat_messages"

    message_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"pchat_{uuid.uuid4().hex[:8]}")
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.patient_id"), index=True)
    role: Mapped[str] = mapped_column(String)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
