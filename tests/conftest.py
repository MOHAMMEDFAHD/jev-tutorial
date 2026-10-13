"""Shared fixtures.

Strategy: we never mock our own Jev wrapper or the SDK. We mock the NETWORK, using an
httpx2.MockTransport inside the real AsyncTypeSafeClient. Every test therefore exercises
the official SDK's request building, response parsing, retries and exception types.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models.decision import Department
from app.services.jev_client import JevClient, build_jev_client
from app.services.questions import HUMAN_REVIEW_CHECKS

Handler = Callable[[httpx2.Request], httpx2.Response]


def make_settings(**overrides) -> Settings:
    base = dict(
        jev_backend="typesafe",
        typesafe_api_key="sk-test-not-a-real-key",
        database_url="sqlite:///:memory:",
        jev_max_retries=0,
        log_level="WARNING",
    )
    base.update(overrides)
    return Settings(_env_file=None, **base)  # ignore any developer .env


def wire_response(
    *,
    department: str = "billing",
    dept_probs: dict[str, float] | None = None,
    dept_confidence: float = 0.9,
    priority_probs: list[float] | None = None,
    priority_confidence: float = 0.9,
    needs_human: float = 0.05,
    human_checks: dict[str, float] | None = None,
    model: str = "jev-1.13.0",
) -> dict:
    """Build a response body in the documented /v1/systemone wire format."""
    # Derived from the enum, so adding a Department doesn't require editing test fixtures.
    dept_probs = dept_probs or {**{d.value: 0.0 for d in Department}, department: 1.0}
    priority_probs = priority_probs or [0.0, 0.0, 1.0, 0.0]
    return {
        "model": model,
        "answers": {
            "department": {
                "type": "choice",
                "choice": department,
                "probabilities": dept_probs,
                "confidence": dept_confidence,
            },
            "priority": {
                "type": "score",
                "score": sum(i * p for i, p in enumerate(priority_probs)),
                "confidence": priority_confidence,
                "legend": {
                    str(i): name for i, name in enumerate(["low", "medium", "high", "critical"])
                },
                "probabilities": {str(i): p for i, p in enumerate(priority_probs)},
            },
            # Four human-review checks: `needs_human` sets all, `human_checks` overrides some.
            **{
                f"needs_human_{name}": {
                    "type": "noul",
                    "noul": (human_checks or {}).get(name, needs_human),
                }
                for name in HUMAN_REVIEW_CHECKS
            },
        },
        "usage": {"input_tokens": 300, "output_tokens": 30},
    }


def respond_with(body: dict | None = None, status: int = 200, **kwargs) -> Handler:
    payload = body if body is not None else wire_response(**kwargs)

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status, json=payload, headers={"x-typesafe-request-id": "req_test"})

    return handler


def jev_with(handler: Handler, **settings_overrides) -> JevClient:
    return build_jev_client(
        make_settings(**settings_overrides), transport=httpx2.MockTransport(handler)
    )


@pytest.fixture
def api_client_factory():
    """Create a TestClient whose Jev calls are answered by `handler`."""
    clients: list[TestClient] = []

    def factory(handler: Handler, **settings_overrides) -> TestClient:
        settings = make_settings(**settings_overrides)
        jev = build_jev_client(settings, transport=httpx2.MockTransport(handler))
        client = TestClient(create_app(settings=settings, jev_client=jev))
        client.__enter__()
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.__exit__(None, None, None)
