import uuid
from datetime import datetime, date

from sqlalchemy import String, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Patient(Base):
    __tablename__ = "patients"

    patient_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"pat_{uuid.uuid4().hex[:8]}")
    mrn: Mapped[str] = mapped_column(String, unique=True)
    display_name: Mapped[str] = mapped_column(String)
    dob: Mapped[date] = mapped_column(Date)
    jurisdiction: Mapped[str] = mapped_column(String, default="US-GENERIC")
    home_region: Mapped[str] = mapped_column(String, default="us-demo")
    family_id: Mapped[str] = mapped_column(String, ForeignKey("family_groups.family_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
