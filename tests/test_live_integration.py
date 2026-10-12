"""LIVE test against the real TypeSafe API. Skipped unless explicitly enabled:

    RUN_LIVE_TESTS=1 TYPESAFE_API_KEY=... pytest -m live

It checks the CONTRACT (types, ranges, our parser accepts the answer), never specific
predictions: model outputs can legitimately change when the jev-latest alias moves.
"""

import os

import pytest

from app.config import Settings
from app.policies.automation_policy import AutomationPolicy
from app.services.decision_parser import parse_ticket_decision
from app.services.jev_client import build_jev_client

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not (os.getenv("RUN_LIVE_TESTS") == "1" and Settings().typesafe_api_key),
        reason="set RUN_LIVE_TESTS=1 and TYPESAFE_API_KEY (in .env or the environment)",
    ),
]


async def test_live_ticket_round_trip():
    jev = build_jev_client(Settings(jev_backend="typesafe"))
    try:
        result = await jev.evaluate_ticket(
            "I was charged twice for my subscription and need a refund."
        )
    finally:
        await jev.aclose()
    decision = parse_ticket_decision(result.response)  # raises if the contract changed
    assert decision.model.startswith("jev")
    assert 0 <= decision.department.confidence <= 1
    action, reasons = AutomationPolicy().evaluate(decision)
    assert reasons
    print(
        f"\nLIVE: {decision.model} -> {decision.department.department} "
        f"({decision.department.confidence:.2f}), {decision.priority.priority}, "
        f"{action}, {result.latency_ms:.0f} ms"
    )
