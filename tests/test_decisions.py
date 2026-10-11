"""decision_parser: native Jev answers -> typed TicketDecision, rejecting anything suspicious."""

import json
import math

import pytest
from typesafe_sdk import SystemOneResponse

from app.models.decision import Department, Priority
from app.services.decision_parser import DecisionValidationError, parse_ticket_decision
from tests.conftest import wire_response

ALL_ZERO = {"billing": 0.0, "technical": 0.0, "account": 0.0, "sales": 0.0, "general": 0.0}


def parse(body: dict):
    # model_validate_json mirrors how the SDK parses HTTP bodies (strict mode, JSON keys).
    return parse_ticket_decision(SystemOneResponse.model_validate_json(json.dumps(body)))


def test_valid_response_becomes_typed_decision():
    decision = parse(
        wire_response(
            department="billing",
            dept_probs={**ALL_ZERO, "billing": 0.85, "technical": 0.15},
            dept_confidence=0.81,
            priority_probs=[0.0, 0.1, 0.8, 0.1],
            priority_confidence=0.7,
            needs_human=0.12,
        )
    )
    assert decision.department.department is Department.BILLING
    assert decision.department.confidence == 0.81
    assert decision.department.top2_margin == pytest.approx(0.70)
    assert decision.priority.priority is Priority.HIGH
    assert decision.priority.probabilities[Priority.CRITICAL] == 0.1
    assert decision.human_review.probability == 0.12
    assert decision.model == "jev-1.13.0"
    assert decision.request_id is None  # no HTTP headers when built directly


def test_priority_uses_most_likely_level_not_rounded_expectation():
    # Bimodal: expectation = 0.5*0 + 0.5*3 = 1.5 -> round() would say "high" (2),
    # a level with zero probability. Argmax picks a level the model actually supports.
    decision = parse(wire_response(priority_probs=[0.51, 0.0, 0.0, 0.49], priority_confidence=0.0))
    assert decision.priority.expected_score == pytest.approx(1.47)
    assert decision.priority.priority is Priority.LOW


def test_unexpected_department_label_is_rejected():
    body = wire_response()
    body["answers"]["department"]["choice"] = "legal"
    with pytest.raises(DecisionValidationError, match="unexpected department"):
        parse(body)


def test_probability_keys_must_match_our_options():
    body = wire_response(dept_probs={"billing": 0.9, "technical": 0.1})
    with pytest.raises(DecisionValidationError, match="probability keys"):
        parse(body)


def test_probabilities_must_sum_to_one():
    body = wire_response(dept_probs={**ALL_ZERO, "billing": 0.6, "technical": 0.6})
    with pytest.raises(DecisionValidationError, match="sum to"):
        parse(body)


def test_choice_must_be_the_argmax():
    body = wire_response(
        department="technical", dept_probs={**ALL_ZERO, "billing": 0.7, "technical": 0.3}
    )
    with pytest.raises(DecisionValidationError, match="not the highest-probability"):
        parse(body)


@pytest.mark.parametrize("bad", [1.5, -0.1, math.nan, math.inf])
def test_confidence_out_of_range_or_not_finite_is_rejected(bad):
    # Verified on SDK 0.7.4: the SDK itself accepts all four values. Our parser must not.
    body = wire_response()
    body["answers"]["department"]["confidence"] = bad
    with pytest.raises(DecisionValidationError, match="department.confidence"):
        parse(body)


def test_missing_prediction_is_rejected():
    body = wire_response()
    del body["answers"]["needs_human"]
    with pytest.raises(DecisionValidationError, match="missing answer for question 'needs_human'"):
        parse(body)


def test_wrong_answer_type_is_rejected():
    body = wire_response()
    body["answers"]["needs_human"] = body["answers"]["department"]
    with pytest.raises(DecisionValidationError, match="expected NoulAnswer"):
        parse(body)


def test_priority_with_wrong_number_of_levels_is_rejected():
    body = wire_response()
    body["answers"]["priority"]["probabilities"] = {"0": 0.5, "1": 0.5}
    with pytest.raises(DecisionValidationError, match="priority: probability keys"):
        parse(body)
