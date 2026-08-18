import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FamilyChatMessage(Base):
    """Persisted so the family Q&A chat has an audit trail like everything
    else in CareThread (spec section 15) — nothing the agent says disappears."""
    __tablename__ = "family_chat_messages"

    message_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"fchat_{uuid.uuid4().hex[:8]}")
    family_id: Mapped[str] = mapped_column(String, ForeignKey("family_groups.family_id"), index=True)
    role: Mapped[str] = mapped_column(String)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
