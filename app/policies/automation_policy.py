"""Decision D - the automation policy: may this ticket be routed without a human?

This is application logic, written in plain Python on purpose:
  * Jev tells us WHAT it thinks and HOW SURE it is.
  * This policy decides WHETHER WE ACT, using business rules the model never sees.

Rules are evaluated independently and ALL fired rules are reported. Any single fired
rule sends the ticket to a human - an uncertain AI decision can never bypass a
mandatory business rule, and a confident AI decision can never bypass one either.

Confidence is not a guarantee of correctness. A ticket routed automatically at 0.95
confidence can still be wrong; the thresholds trade automation volume against the
error rate you are willing to accept, and must be tuned with evaluation data.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.models.decision import Action, Priority, TicketDecision


# Reason codes are stable strings: they are stored, aggregated in metrics and shown to reviewers.
class Reason:
    MANDATORY_PRIORITY = "mandatory_review_priority"
    CRITICAL_RISK = "critical_probability_above_limit"
    HUMAN_REQUESTED = "model_flagged_human_needed"
    LOW_DEPARTMENT_CONFIDENCE = "low_department_confidence"
    AMBIGUOUS_DEPARTMENT = "ambiguous_department_top2"
    LOW_PRIORITY_CONFIDENCE = "low_priority_confidence"
    ALL_CHECKS_PASSED = "all_checks_passed"


@dataclass(frozen=True)
class AutomationPolicy:
    auto_route_min_confidence: float = 0.60
    min_top2_margin: float = 0.15
    priority_min_confidence: float = 0.40
    human_review_noul_threshold: float = 0.50
    critical_escalation_probability: float = 0.25
    mandatory_review_priorities: frozenset[Priority] = frozenset({Priority.CRITICAL})

    @classmethod
    def from_settings(cls, settings: Settings) -> AutomationPolicy:
        return cls(
            auto_route_min_confidence=settings.auto_route_min_confidence,
            min_top2_margin=settings.min_top2_margin,
            priority_min_confidence=settings.priority_min_confidence,
            human_review_noul_threshold=settings.human_review_noul_threshold,
            critical_escalation_probability=settings.critical_escalation_probability,
            mandatory_review_priorities=frozenset(
                Priority(p) for p in settings.mandatory_review_priorities
            ),
        )

    def evaluate(self, decision: TicketDecision) -> tuple[Action, list[str]]:
        reasons: list[str] = []
        dept, prio = decision.department, decision.priority

        # 1. Business rules: independent of model confidence.
        if prio.priority in self.mandatory_review_priorities:
            reasons.append(Reason.MANDATORY_PRIORITY)
        if prio.probabilities.get(Priority.CRITICAL, 0.0) >= self.critical_escalation_probability:
            # Look at the whole distribution, not just the argmax: a 30% chance of a
            # security incident is worth a human's attention even if "high" won.
            reasons.append(Reason.CRITICAL_RISK)

        # 2. The model's own yes/no judgment that a human is needed (Noul probability).
        if decision.human_review.probability >= self.human_review_noul_threshold:
            reasons.append(Reason.HUMAN_REQUESTED)

        # 3. Uncertainty gates: the model isn't sure enough for us to act.
        if dept.confidence < self.auto_route_min_confidence:
            reasons.append(Reason.LOW_DEPARTMENT_CONFIDENCE)
        if dept.top2_margin < self.min_top2_margin:
            reasons.append(Reason.AMBIGUOUS_DEPARTMENT)  # two departments nearly tied
        if prio.confidence < self.priority_min_confidence:
            reasons.append(Reason.LOW_PRIORITY_CONFIDENCE)  # can't set an SLA reliably

        if reasons:
            return Action.HUMAN_REVIEW, reasons
        return Action.AUTO_ROUTE, [Reason.ALL_CHECKS_PASSED]
