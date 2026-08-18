import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FamilyGroup(Base):
    __tablename__ = "family_groups"

    family_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"fam_{uuid.uuid4().hex[:8]}")
    family_name: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FamilyRelationship(Base):
    __tablename__ = "family_relationships"

    relationship_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"rel_{uuid.uuid4().hex[:8]}")
    family_id: Mapped[str] = mapped_column(String, ForeignKey("family_groups.family_id"), index=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.patient_id"), index=True)
    related_patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.patient_id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String)  # PARENT | CHILD | SIBLING
    notes: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
