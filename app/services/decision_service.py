"""The decision pipeline: sanitize -> ask Jev -> validate -> apply policy -> route.

`process()` never raises because of the model. If Jev is slow, down, rate limited,
misconfigured, or returns something we can't trust, the ticket is still accepted and
sent to a human queue with the failure reason recorded (graceful degradation).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.models.decision import Action, TicketDecision
from app.models.ticket import TicketStatus
from app.policies.automation_policy import AutomationPolicy
from app.services.decision_parser import parse_ticket_decision
from app.services.jev_client import JevAuthError, JevClient, JevError
from app.services.routing_service import route_ticket

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProcessingResult:
    decision: TicketDecision | None
    action: Action
    queue: str
    reasons: list[str]
    status: TicketStatus
    latency_ms: float | None
    error_reason: str | None = None

    @property
    def model(self) -> str | None:
        return self.decision.model if self.decision else None


class DecisionService:
    def __init__(self, jev: JevClient, policy: AutomationPolicy) -> None:
        self.jev = jev
        self.policy = policy

    async def process(self, ticket_id: str, sanitized_message: str) -> ProcessingResult:
        try:
            result = await self.jev.evaluate_ticket(sanitized_message)
            decision = parse_ticket_decision(result.response)
        except JevError as exc:
            log = logger.error if isinstance(exc, JevAuthError) else logger.warning
            log("jev_inference_failed", extra={"fields": {
                "ticket_id": ticket_id, "reason": exc.reason, "detail": str(exc),
                "jev_request_id": exc.request_id}})
            return ProcessingResult(
                decision=None,
                action=Action.HUMAN_REVIEW,
                queue=route_ticket(None, Action.HUMAN_REVIEW),
                reasons=[exc.reason],
                status=TicketStatus.INFERENCE_FAILED,
                latency_ms=None,
                error_reason=exc.reason,
            )

        action, reasons = self.policy.evaluate(decision)
        queue = route_ticket(decision, action)
        logger.info("ticket_decided", extra={"fields": {
            "ticket_id": ticket_id,
            "department": decision.department.department,
            "department_confidence": decision.department.confidence,
            "priority": decision.priority.priority,
            "human_review_p": decision.human_review.probability,
            "action": action, "queue": queue, "reasons": reasons,
            "model": decision.model, "jev_request_id": decision.request_id,
            "latency_ms": round(result.latency_ms, 1)}})
        return ProcessingResult(
            decision=decision,
            action=action,
            queue=queue,
            reasons=reasons,
            status=TicketStatus.ROUTED if action is Action.AUTO_ROUTE else TicketStatus.PENDING_REVIEW,
            latency_ms=result.latency_ms,
        )
