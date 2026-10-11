"""Convert a native SystemOneResponse into our typed TicketDecision - or refuse to.

The SDK already guarantees structural shape (it raises TypeSafeAPIResponseValidationError
on missing fields). This layer checks the things only WE know:
  * every question we asked has an answer of the right type,
  * the chosen option is one of OUR enum values (no surprise labels),
  * the probability map covers exactly our options and is a real distribution,
  * the reported choice is consistent with the probabilities,
  * all numbers are finite and in range.
Anything else raises DecisionValidationError. We never "fix up" a bad answer.
"""

from __future__ import annotations

import math

from typesafe_sdk import ChoiceAnswer, NoulAnswer, ScoreAnswer, SystemOneResponse, TypeSafeError

from app.models.decision import (
    Department,
    DepartmentDecision,
    HumanReviewSignal,
    Priority,
    PriorityDecision,
    TicketDecision,
)
from app.services.jev_client import JevResponseError
from app.services.questions import DEPARTMENT_KEY, HUMAN_REVIEW_KEY, PRIORITY_KEY

PROBABILITY_SUM_TOLERANCE = 0.02  # API docs: probabilities "sum to approximately 1"


class DecisionValidationError(JevResponseError):
    reason = "decision_validation_failed"


def _check_unit(value: float, name: str) -> float:
    if not isinstance(value, int | float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise DecisionValidationError(f"{name}={value!r} is not a finite number in [0, 1]")
    return float(value)


def _check_distribution(probabilities: dict, expected_keys: set, name: str) -> None:
    if set(probabilities) != expected_keys:
        raise DecisionValidationError(
            f"{name}: probability keys {sorted(map(str, probabilities))} "
            f"!= expected {sorted(map(str, expected_keys))}"
        )
    for key, value in probabilities.items():
        _check_unit(value, f"{name}.probabilities[{key}]")
    total = sum(probabilities.values())
    if abs(total - 1.0) > PROBABILITY_SUM_TOLERANCE:
        raise DecisionValidationError(f"{name}: probabilities sum to {total:.3f}, not ~1")


def _get(response: SystemOneResponse, key: str, kind: type):
    answer = response.answers.get(key)
    if answer is None:
        raise DecisionValidationError(f"missing answer for question '{key}'")
    if not isinstance(answer, kind):
        raise DecisionValidationError(
            f"'{key}' is {type(answer).__name__}, expected {kind.__name__}"
        )
    return answer


def parse_department(answer: ChoiceAnswer) -> DepartmentDecision:
    allowed = {d.value for d in Department}
    if answer.choice not in allowed:
        raise DecisionValidationError(f"unexpected department {answer.choice!r}")
    _check_distribution(answer.probabilities, allowed, "department")
    confidence = _check_unit(answer.confidence, "department.confidence")

    ranked = sorted(answer.probabilities.values(), reverse=True)
    if answer.probabilities[answer.choice] < ranked[0] - 1e-9:
        raise DecisionValidationError("department.choice is not the highest-probability option")

    return DepartmentDecision(
        department=Department(answer.choice),
        confidence=confidence,
        probabilities={Department(k): v for k, v in answer.probabilities.items()},
        top2_margin=round(ranked[0] - ranked[1], 6),
    )


def parse_priority(answer: ScoreAnswer) -> PriorityDecision:
    levels = set(range(len(Priority)))
    # SDK 0.7.x parses the wire's string level keys ("0".."3") into ints.
    _check_distribution(answer.probabilities, levels, "priority")
    confidence = _check_unit(answer.confidence, "priority.confidence")
    if not math.isfinite(answer.score) or not 0 <= answer.score <= len(Priority) - 1:
        raise DecisionValidationError(f"priority.score={answer.score!r} out of range")

    # Use the MOST LIKELY level, not round(score): TypeSafe warns not to interpolate
    # between Score levels. The expected score is kept for thresholds and audit.
    most_likely = max(answer.probabilities, key=answer.probabilities.get)
    return PriorityDecision(
        priority=Priority.from_level(most_likely),
        expected_score=answer.score,
        confidence=confidence,
        probabilities={Priority.from_level(k): v for k, v in answer.probabilities.items()},
    )


def _request_id(response: SystemOneResponse) -> str | None:
    """`response.request_id` raises TypeSafeError if the header is absent (verified on
    SDK 0.7.4), so read it defensively; it is useful for support tickets, not required."""
    try:
        return response.request_id
    except TypeSafeError:
        return None


def parse_ticket_decision(response: SystemOneResponse) -> TicketDecision:
    noul = _get(response, HUMAN_REVIEW_KEY, NoulAnswer)
    return TicketDecision(
        department=parse_department(_get(response, DEPARTMENT_KEY, ChoiceAnswer)),
        priority=parse_priority(_get(response, PRIORITY_KEY, ScoreAnswer)),
        human_review=HumanReviewSignal(probability=_check_unit(noul.noul, "needs_human.noul")),
        model=response.model,
        request_id=_request_id(response),
        input_tokens=response.usage.input_tokens,
    )
