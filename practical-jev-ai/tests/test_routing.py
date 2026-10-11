"""Automation policy (Decision D) and the routing service."""

import pytest

from app.models.decision import (
    Action,
    Department,
    DepartmentDecision,
    HumanReviewSignal,
    Priority,
    PriorityDecision,
    TicketDecision,
)
from app.policies.automation_policy import AutomationPolicy, Reason
from app.services.routing_service import (
    DEPARTMENT_QUEUES,
    ESCALATION_QUEUE,
    HUMAN_REVIEW_QUEUE,
    route_ticket,
)


def decision(
    department=Department.BILLING,
    dept_confidence=0.9,
    margin=0.8,
    priority=Priority.MEDIUM,
    priority_confidence=0.9,
    p_critical=0.0,
    needs_human=0.05,
) -> TicketDecision:
    prio_probs = {p: 0.0 for p in Priority}
    prio_probs[priority] = 1.0 - p_critical if priority is not Priority.CRITICAL else 1.0
    if priority is not Priority.CRITICAL:
        prio_probs[Priority.CRITICAL] = p_critical
    return TicketDecision(
        department=DepartmentDecision(
            department=department,
            confidence=dept_confidence,
            probabilities={department: 0.9},
            top2_margin=margin,
        ),
        priority=PriorityDecision(
            priority=priority,
            expected_score=float(list(Priority).index(priority)),
            confidence=priority_confidence,
            probabilities=prio_probs,
        ),
        human_review=HumanReviewSignal(probability=needs_human),
        model="jev-1.13.0",
    )


POLICY = AutomationPolicy()


def test_confident_routine_ticket_is_auto_routed():
    action, reasons = POLICY.evaluate(decision())
    assert action is Action.AUTO_ROUTE
    assert reasons == [Reason.ALL_CHECKS_PASSED]


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"dept_confidence": 0.45}, Reason.LOW_DEPARTMENT_CONFIDENCE),
        ({"margin": 0.05}, Reason.AMBIGUOUS_DEPARTMENT),
        ({"priority_confidence": 0.2}, Reason.LOW_PRIORITY_CONFIDENCE),
        ({"needs_human": 0.7}, Reason.HUMAN_REQUESTED),
        ({"p_critical": 0.3, "priority": Priority.HIGH}, Reason.CRITICAL_RISK),
    ],
)
def test_each_rule_alone_forces_human_review(kwargs, reason):
    action, reasons = POLICY.evaluate(decision(**kwargs))
    assert action is Action.HUMAN_REVIEW
    assert reason in reasons


def test_mandatory_business_rule_beats_perfect_confidence():
    action, reasons = POLICY.evaluate(
        decision(priority=Priority.CRITICAL, dept_confidence=1.0, priority_confidence=1.0)
    )
    assert action is Action.HUMAN_REVIEW
    assert Reason.MANDATORY_PRIORITY in reasons


def test_all_fired_reasons_are_reported():
    _, reasons = POLICY.evaluate(decision(dept_confidence=0.3, margin=0.01, needs_human=0.9))
    assert set(reasons) == {
        Reason.LOW_DEPARTMENT_CONFIDENCE,
        Reason.AMBIGUOUS_DEPARTMENT,
        Reason.HUMAN_REQUESTED,
    }


def test_threshold_is_configurable():
    lenient = AutomationPolicy(auto_route_min_confidence=0.4)
    strict = AutomationPolicy(auto_route_min_confidence=0.95)
    d = decision(dept_confidence=0.7)
    assert lenient.evaluate(d)[0] is Action.AUTO_ROUTE
    assert strict.evaluate(d)[0] is Action.HUMAN_REVIEW


def test_boundary_value_is_inclusive_for_routing():
    # confidence == threshold is "sure enough"; just below is not.
    assert POLICY.evaluate(decision(dept_confidence=0.60))[0] is Action.AUTO_ROUTE
    assert POLICY.evaluate(decision(dept_confidence=0.5999))[0] is Action.HUMAN_REVIEW


@pytest.mark.parametrize(
    ("department", "queue"),
    [
        (Department.BILLING, "billing_queue"),
        (Department.TECHNICAL, "technical_queue"),
        (Department.ACCOUNT, "account_queue"),
        (Department.SALES, "sales_queue"),
        (Department.GENERAL, "general_queue"),
    ],
)
def test_auto_routed_tickets_go_to_department_queue(department, queue):
    assert route_ticket(decision(department=department), Action.AUTO_ROUTE) == queue


def test_every_department_has_its_own_queue():
    """Guard: a new Department without a queue would silently fall back to general_queue."""
    assert set(DEPARTMENT_QUEUES) == set(Department)


def test_review_tickets_never_reach_a_department_queue():
    assert route_ticket(decision(), Action.HUMAN_REVIEW) == HUMAN_REVIEW_QUEUE


def test_critical_review_tickets_are_escalated():
    d = decision(priority=Priority.CRITICAL)
    assert route_ticket(d, Action.HUMAN_REVIEW) == ESCALATION_QUEUE


def test_missing_decision_falls_back_to_human_review():
    assert route_ticket(None, Action.AUTO_ROUTE) == HUMAN_REVIEW_QUEUE
