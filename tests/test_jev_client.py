"""JevClient: request shape, success parsing, and SDK-exception -> app-exception mapping."""

import json

import httpx2
import pytest

from app.config import Settings
from app.models.decision import Department
from app.services.jev_client import (
    JevAuthError,
    JevBadRequestError,
    JevRateLimitError,
    JevResponseError,
    JevTimeoutError,
    JevUnavailableError,
    build_jev_client,
)
from tests.conftest import jev_with, respond_with, wire_response


async def test_sends_documented_request_shape():
    captured = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content)
        return httpx2.Response(200, json=wire_response())

    await jev_with(handler).evaluate_ticket("I was charged twice")

    assert captured["url"] == "https://api.typesafe.ai/v1/systemone"
    assert captured["auth"] == "Bearer sk-test-not-a-real-key"
    body = captured["body"]
    assert body["model"] == "jev-latest"
    assert body["state"] == {"customer_message": "I was charged twice"}
    assert {k: q["type"] for k, q in body["questions"].items()} == {
        "department": "choice",
        "priority": "score",
        "needs_human_legal_threat": "noul",
        "needs_human_fraud_or_takeover": "noul",
        "needs_human_compensation_request": "noul",
        "needs_human_manager_request": "noul",
    }
    assert set(body["questions"]["department"]["criteria"]) == {d.value for d in Department}
    assert len(body["questions"]["priority"]["criteria"]) == 4


async def test_success_returns_parsed_sdk_response_and_latency():
    result = await jev_with(respond_with(department="technical")).evaluate_ticket("x")
    assert result.response.choices["department"].choice == "technical"
    assert result.response.model == "jev-1.13.0"
    assert result.latency_ms >= 0


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, JevAuthError),
        (403, JevAuthError),
        (400, JevBadRequestError),
        (422, JevBadRequestError),
        (429, JevRateLimitError),
        (500, JevUnavailableError),
        (529, JevUnavailableError),  # TypeSafe's "overloaded" status
    ],
)
async def test_http_errors_map_to_app_errors(status, expected):
    with pytest.raises(expected) as info:
        await jev_with(respond_with({"detail": "x"}, status=status)).evaluate_ticket("x")
    assert info.value.request_id == "req_test"


async def test_timeout_maps_to_jev_timeout():
    def handler(request):
        raise httpx2.ReadTimeout("slow", request=request)

    with pytest.raises(JevTimeoutError):
        await jev_with(handler).evaluate_ticket("x")


async def test_connection_failure_maps_to_unavailable():
    def handler(request):
        raise httpx2.ConnectError("refused", request=request)

    with pytest.raises(JevUnavailableError):
        await jev_with(handler).evaluate_ticket("x")


async def test_structurally_malformed_response_is_rejected_by_sdk():
    body = {
        "model": "jev-1.13.0",
        "usage": {},
        "answers": {"needs_human_legal_threat": {"type": "noul"}},
    }
    with pytest.raises(JevResponseError):
        await jev_with(respond_with(body)).evaluate_ticket("x")


async def test_sdk_retries_transient_rate_limit_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx2.Response(429, json={}, headers={"retry-after-ms": "1"})
        return httpx2.Response(200, json=wire_response())

    result = await jev_with(handler, jev_max_retries=2).evaluate_ticket("x")
    assert calls["n"] == 2
    assert result.response.choices["department"].choice == "billing"


async def test_persistent_rate_limit_raises_after_retry_budget():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx2.Response(429, json={}, headers={"retry-after-ms": "1"})

    with pytest.raises(JevRateLimitError):
        await jev_with(handler, jev_max_retries=2).evaluate_ticket("x")
    assert calls["n"] == 3  # initial attempt + 2 retries


def test_missing_api_key_fails_fast_with_helpful_message():
    settings = Settings(_env_file=None, jev_backend="typesafe", typesafe_api_key=None)
    with pytest.raises(JevAuthError, match="TYPESAFE_API_KEY is not set"):
        build_jev_client(settings)


def test_malformed_api_key_is_rejected_by_sdk_before_any_request():
    settings = Settings(_env_file=None, jev_backend="typesafe", typesafe_api_key="bad key")
    with pytest.raises(JevAuthError, match="malformed"):
        build_jev_client(settings)


def test_api_key_is_not_exposed_in_settings_repr():
    settings = Settings(_env_file=None, typesafe_api_key="sk-super-secret")
    assert "sk-super-secret" not in repr(settings)
