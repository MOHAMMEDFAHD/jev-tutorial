"""All database access goes through this class (easy to mock, easy to swap the database)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database.models import TicketRecord
from app.models.ticket import MetricsResponse, ReviewRequest, TicketCreate, TicketStatus
from app.services.decision_service import ProcessingResult


class TicketRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    def get(self, ticket_id: str) -> TicketRecord | None:
        with self._sessions() as session:
            return session.get(TicketRecord, ticket_id)

    def list(self, *, status: str | None, limit: int, offset: int) -> list[TicketRecord]:
        query = select(TicketRecord).order_by(TicketRecord.created_at.desc())
        if status:
            query = query.where(TicketRecord.status == status)
        with self._sessions() as session:
            return list(session.scalars(query.limit(limit).offset(offset)))

    def create(
        self, ticket: TicketCreate, *, sanitized: str, fingerprint: str, result: ProcessingResult
    ) -> tuple[TicketRecord, bool]:
        """Insert once. Returns (record, created). If a concurrent request inserted the same
        ticket_id first, the primary-key violation is caught and the existing row returned."""
        d = result.decision
        record = TicketRecord(
            ticket_id=ticket.ticket_id,
            customer_id=ticket.customer_id,
            content_sha256=fingerprint,
            sanitized_message=sanitized,
            department=d.department.department.value if d else None,
            department_confidence=d.department.confidence if d else None,
            department_probabilities=(
                {k.value: v for k, v in d.department.probabilities.items()} if d else None
            ),
            priority=d.priority.priority.value if d else None,
            priority_score=d.priority.expected_score if d else None,
            priority_confidence=d.priority.confidence if d else None,
            human_review_probability=d.human_review.probability if d else None,
            model=d.model if d else None,
            jev_request_id=d.request_id if d else None,
            input_tokens=d.input_tokens if d else None,
            latency_ms=result.latency_ms,
            action=result.action.value,
            queue=result.queue,
            reasons=list(result.reasons),
            status=result.status.value,
            error_reason=result.error_reason,
        )
        with self._sessions() as session:
            session.add(record)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.get(TicketRecord, ticket.ticket_id)
                if existing is None:  # not a duplicate key: a genuine integrity problem
                    raise
                return existing, False
            return record, True

    def record_review(self, ticket_id: str, review: ReviewRequest) -> TicketRecord | None:
        with self._sessions() as session:
            record = session.get(TicketRecord, ticket_id)
            if record is None:
                return None
            record.reviewer = review.reviewer
            record.final_department = review.final_department.value
            record.final_priority = review.final_priority.value
            record.review_notes = review.notes
            record.reviewed_at = datetime.now(UTC)
            record.status = TicketStatus.REVIEWED.value
            session.commit()
            return record

    def metrics(self) -> MetricsResponse:
        with self._sessions() as session:
            by_status = dict(
                session.execute(
                    select(TicketRecord.status, func.count()).group_by(TicketRecord.status)
                ).all()
            )
            by_action = dict(
                session.execute(
                    select(TicketRecord.action, func.count()).group_by(TicketRecord.action)
                ).all()
            )
            failed = session.scalar(
                select(func.count()).where(TicketRecord.error_reason.is_not(None))
            )
            reviews = session.execute(
                select(TicketRecord.department, TicketRecord.final_department).where(
                    TicketRecord.reviewed_at.is_not(None), TicketRecord.department.is_not(None)
                )
            ).all()
            latencies = sorted(
                session.scalars(
                    select(TicketRecord.latency_ms).where(TicketRecord.latency_ms.is_not(None))
                )
            )
        total = sum(by_status.values())
        auto = by_action.get("auto_route", 0)
        return MetricsResponse(
            total_tickets=total,
            by_status=by_status,
            automation_coverage=auto / total if total else 0.0,
            review_rate=(total - auto) / total if total else 0.0,
            inference_error_rate=(failed or 0) / total if total else 0.0,
            reviewed_tickets=len(reviews),
            reviewer_agreement=(
                sum(model == final for model, final in reviews) / len(reviews) if reviews else None
            ),
            latency_ms_p50=_percentile(latencies, 50),
            latency_ms_p95=_percentile(latencies, 95),
        )


def _percentile(sorted_values: list[float], pct: float) -> float | None:
    if not sorted_values:
        return None
    index = min(len(sorted_values) - 1, round(pct / 100 * (len(sorted_values) - 1)))
    return round(sorted_values[index], 2)
