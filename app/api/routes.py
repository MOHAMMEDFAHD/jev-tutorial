"""REST endpoints. Routes stay thin: validate -> call services -> map to response models."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text

from app.config import Settings
from app.database.models import TicketRecord
from app.database.repository import TicketRepository
from app.models.decision import Action
from app.models.ticket import (
    MetricsResponse,
    ReviewRequest,
    TicketCreate,
    TicketResponse,
    TicketStatus,
)
from app.services.decision_service import DecisionService
from app.utils.privacy import content_fingerprint, redact_pii

router = APIRouter()


# ---- Dependency injection: objects are created once in main.py's lifespan -------------
def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_repository(request: Request) -> TicketRepository:
    return request.app.state.repository


def get_decision_service(request: Request) -> DecisionService:
    return request.app.state.decision_service


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
RepoDep = Annotated[TicketRepository, Depends(get_repository)]
ServiceDep = Annotated[DecisionService, Depends(get_decision_service)]


def to_response(record: TicketRecord) -> TicketResponse:
    return TicketResponse(
        ticket_id=record.ticket_id,
        status=TicketStatus(record.status),
        action=Action(record.action),
        queue=record.queue,
        department=record.department,
        priority=record.priority,
        requires_human_review=record.action == Action.HUMAN_REVIEW,
        confidence=record.department_confidence,
        reasons=record.reasons,
        model=record.model,
        created_at=record.created_at,
        review_outcome=(
            f"{record.final_department}/{record.final_priority} by {record.reviewer}"
            if record.reviewed_at else None
        ),
    )


def _replay_or_conflict(record: TicketRecord, fingerprint: str, response: Response) -> TicketResponse:
    """Same ticket_id + same content = safe client retry: return the stored result, do
    NOT re-run the model or re-route. Same id + different content = client bug: 409."""
    if record.content_sha256 != fingerprint:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"ticket_id {record.ticket_id} already exists with different content",
        )
    response.status_code = status.HTTP_200_OK
    response.headers["Idempotent-Replay"] = "true"
    return to_response(record)


@router.post(
    "/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "Idempotent replay of an existing ticket"},
               409: {"description": "ticket_id reused with different content"}},
)
async def create_ticket(
    ticket: TicketCreate, response: Response, settings: SettingsDep,
    repo: RepoDep, service: ServiceDep,
) -> TicketResponse:
    if len(ticket.message) > settings.max_message_chars:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"message exceeds {settings.max_message_chars} characters",
        )
    fingerprint = content_fingerprint(ticket.message)

    existing = await run_in_threadpool(repo.get, ticket.ticket_id)
    if existing is not None:
        return _replay_or_conflict(existing, fingerprint, response)

    sanitized = redact_pii(ticket.message) if settings.redact_pii else ticket.message
    result = await service.process(ticket.ticket_id, sanitized)

    record, created = await run_in_threadpool(
        repo.create, ticket, sanitized=sanitized, fingerprint=fingerprint, result=result
    )
    if not created:  # lost a race with a concurrent identical request
        return _replay_or_conflict(record, fingerprint, response)
    return to_response(record)


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, repo: RepoDep) -> TicketResponse:
    record = await run_in_threadpool(repo.get, ticket_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="ticket not found")
    return to_response(record)


@router.get("/tickets", response_model=list[TicketResponse])
async def list_tickets(
    repo: RepoDep,
    status_filter: Annotated[TicketStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TicketResponse]:
    records = await run_in_threadpool(
        lambda: repo.list(
            status=status_filter.value if status_filter else None, limit=limit, offset=offset
        )
    )
    return [to_response(r) for r in records]


@router.post("/tickets/{ticket_id}/review", response_model=TicketResponse)
async def review_ticket(ticket_id: str, review: ReviewRequest, repo: RepoDep) -> TicketResponse:
    """Record a human verdict. These verdicts are the labels you evaluate the model against."""
    record = await run_in_threadpool(repo.record_review, ticket_id, review)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="ticket not found")
    return to_response(record)


@router.get("/metrics", response_model=MetricsResponse)
async def metrics(repo: RepoDep) -> MetricsResponse:
    return await run_in_threadpool(repo.metrics)


@router.get("/health")
async def health(request: Request, settings: SettingsDep) -> dict:
    """Liveness + readiness of local dependencies. Deliberately does NOT call Jev: a health
    check that spends API quota and fails when TypeSafe blips would cause restart loops,
    and the app degrades gracefully without Jev anyway."""
    def ping() -> None:
        with request.app.state.engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    await run_in_threadpool(ping)  # SQLAlchemyError -> 503 via the global handler
    return {
        "status": "ok",
        "database": "ok",
        "jev_backend": settings.jev_backend,
        "jev_model": settings.jev_model if settings.jev_backend == "typesafe" else "mock-offline",
    }
