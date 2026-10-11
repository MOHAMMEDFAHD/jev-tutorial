"""ORM model: one row per ticket = the audit record of what the system decided and why."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TicketRecord(Base):
    __tablename__ = "tickets"

    # ticket_id is the idempotency key: the primary key makes duplicates impossible.
    ticket_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), index=True)
    content_sha256: Mapped[str] = mapped_column(String(64))
    sanitized_message: Mapped[str] = mapped_column(Text)  # PII-redacted, never the original

    # Model output (nullable: absent when inference failed)
    department: Mapped[str | None] = mapped_column(String(32))
    department_confidence: Mapped[float | None] = mapped_column(Float)
    department_probabilities: Mapped[dict | None] = mapped_column(JSON)
    priority: Mapped[str | None] = mapped_column(String(16))
    priority_score: Mapped[float | None] = mapped_column(Float)
    priority_confidence: Mapped[float | None] = mapped_column(Float)
    human_review_probability: Mapped[float | None] = mapped_column(Float)
    model: Mapped[str | None] = mapped_column(String(64))     # versioned id, e.g. jev-1.13.0
    jev_request_id: Mapped[str | None] = mapped_column(String(128))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[float | None] = mapped_column(Float)

    # Application decision
    action: Mapped[str] = mapped_column(String(32), index=True)
    queue: Mapped[str] = mapped_column(String(64))
    reasons: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), index=True)
    error_reason: Mapped[str | None] = mapped_column(String(64))

    # Human-in-the-loop
    reviewer: Mapped[str | None] = mapped_column(String(64))
    final_department: Mapped[str | None] = mapped_column(String(32))
    final_priority: Mapped[str | None] = mapped_column(String(16))
    review_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
