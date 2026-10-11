"""HTTP request/response schemas for the REST API."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.models.decision import Action, Department, Priority

ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class TicketStatus(StrEnum):
    ROUTED = "routed"                    # auto-routed by policy
    PENDING_REVIEW = "pending_review"    # held for a human by policy
    INFERENCE_FAILED = "inference_failed"  # Jev unavailable/invalid -> held for a human
    REVIEWED = "reviewed"                # a human has signed off


class TicketCreate(BaseModel):
    ticket_id: str = Field(pattern=ID_PATTERN, examples=["TICKET-001"])
    customer_id: str = Field(pattern=ID_PATTERN, examples=["CUSTOMER-100"])
    # The hard upper bound here protects the server; the configurable limit
    # (MAX_MESSAGE_CHARS) is enforced in the route so it can be tuned per deployment.
    message: str = Field(
        min_length=1,
        max_length=20_000,
        examples=["I was charged twice for my subscription and need a refund."],
    )

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must contain non-whitespace text")
        return value.strip()


class TicketResponse(BaseModel):
    ticket_id: str
    status: TicketStatus
    action: Action
    queue: str
    department: Department | None
    priority: Priority | None
    requires_human_review: bool
    confidence: float | None = Field(description="Jev's confidence in the department decision")
    reasons: list[str]
    model: str | None
    created_at: datetime
    review_outcome: str | None = None


class ReviewRequest(BaseModel):
    """A human's verdict on a ticket. Becomes ground truth for future evaluation."""

    reviewer: str = Field(pattern=ID_PATTERN)
    final_department: Department
    final_priority: Priority
    notes: str | None = Field(default=None, max_length=1000)


class MetricsResponse(BaseModel):
    total_tickets: int
    by_status: dict[str, int]
    automation_coverage: float   # share of tickets auto-routed
    review_rate: float           # share held for humans (incl. inference failures)
    inference_error_rate: float
    reviewed_tickets: int
    reviewer_agreement: float | None  # share of reviews where human kept model's department
    latency_ms_p50: float | None
    latency_ms_p95: float | None
