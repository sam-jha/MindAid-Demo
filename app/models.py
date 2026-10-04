"""The four database tables."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))  # "patient" or "psychologist"
    email: Mapped[str] = mapped_column(String(254), unique=True)  # stored lower-case
    password_hash: Mapped[str] = mapped_column(String(255))  # salted scrypt hash, never the password
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class Entry(Base):
    __tablename__ = "entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    patient: Mapped["User"] = relationship()  # lets a summariser see whose entries these are


class ConsentAcknowledgement(Base):
    __tablename__ = "consent_acknowledgements"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    notice_version: Mapped[str] = mapped_column(String(20))
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Summary(Base):
    __tablename__ = "summaries"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    generated_by: Mapped[str] = mapped_column(String(100))  # "fake" or a model name
    entries_covered_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entries_covered_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content: Mapped[dict] = mapped_column(JSON)  # the structured summary
    # urgent | notable | routine | unassessed
    priority_level: Mapped[str] = mapped_column(String(20), default="unassessed")
    priority_reason: Mapped[str] = mapped_column(Text, default="")
