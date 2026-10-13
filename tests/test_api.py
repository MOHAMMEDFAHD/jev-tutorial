"""End-to-end HTTP tests: FastAPI + services + policy + SQLite, Jev mocked at the network."""

import json

import httpx2
import pytest
from sqlalchemy.exc import OperationalError

from tests.conftest import respond_with, wire_response

TICKET = {
    "ticket_id": "TICKET-001",
    "customer_id": "CUSTOMER-100",
    "message": "I was charged twice for my subscription and need a refund.",
}
CONFIDENT_BILLING = dict(
    department="billing",
    dept_confidence=0.95,
    priority_probs=[0.0, 0.05, 0.95, 0.0],
    priority_confidence=0.9,
    needs_human=0.04,
)


def test_confident_ticket_is_auto_routed_and_persisted(api_client_factory):
    client = api_client_factory(respond_with(**CONFIDENT_BILLING))
    response = client.post("/tickets", json=TICKET)
    assert response.status_code == 201
    body = response.json()
    assert body["department"] == "billing"
    assert body["priority"] == "high"
    assert body["action"] == "auto_route"
    assert body["queue"] == "billing_queue"
    assert body["requires_human_review"] is False
    assert body["confidence"] == 0.95  # comes from the (mocked) model response
    assert body["model"] == "jev-1.13.0"
    assert body["status"] == "routed"

    stored = client.get("/tickets/TICKET-001").json()
    assert stored == body


def test_low_confidence_ticket_is_held_for_review(api_client_factory):
    client = api_client_factory(respond_with(**{**CONFIDENT_BILLING, "dept_confidence": 0.3}))
    body = client.post("/tickets", json=TICKET).json()
    assert body["action"] == "human_review"
    assert body["queue"] == "human_review_queue"
    assert body["status"] == "pending_review"
    assert "low_department_confidence" in body["reasons"]


def test_threshold_from_settings_changes_outcome(api_client_factory):
    client = api_client_factory(
        respond_with(**{**CONFIDENT_BILLING, "dept_confidence": 0.7}),
        auto_route_min_confidence=0.9,
    )
    assert client.post("/tickets", json=TICKET).json()["action"] == "human_review"


@pytest.mark.parametrize(
    ("handler", "reason"),
    [
        (respond_with({"detail": "bad key"}, status=401), "jev_auth_failed"),
        (respond_with({"detail": "slow down"}, status=429), "jev_rate_limited"),
        (respond_with({"detail": "boom"}, status=500), "jev_unavailable"),
        (respond_with({"model": "x", "usage": {}, "answers": {}}), "decision_validation_failed"),
    ],
)
def test_jev_failures_degrade_to_human_review(api_client_factory, handler, reason):
    client = api_client_factory(handler)
    response = client.post("/tickets", json=TICKET)
    assert response.status_code == 201  # the ticket is accepted, not lost
    body = response.json()
    assert body["status"] == "inference_failed"
    assert body["action"] == "human_review"
    assert body["department"] is None
    assert body["reasons"] == [reason]


def test_timeout_degrades_to_human_review(api_client_factory):
    def slow(request):
        raise httpx2.ReadTimeout("slow", request=request)

    body = api_client_factory(slow).post("/tickets", json=TICKET).json()
    assert body["reasons"] == ["jev_timeout"]


def test_retrying_same_ticket_does_not_call_jev_twice(api_client_factory):
    calls = {"n": 0}

    def counting(request):
        calls["n"] += 1
        return httpx2.Response(200, json=wire_response(**CONFIDENT_BILLING))

    client = api_client_factory(counting)
    first = client.post("/tickets", json=TICKET)
    second = client.post("/tickets", json=TICKET)
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.headers["Idempotent-Replay"] == "true"
    assert second.json() == first.json()
    assert calls["n"] == 1  # no second inference, no second routing action


def test_reusing_ticket_id_with_different_content_is_rejected(api_client_factory):
    client = api_client_factory(respond_with(**CONFIDENT_BILLING))
    client.post("/tickets", json=TICKET)
    response = client.post("/tickets", json={**TICKET, "message": "Different text"})
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {**TICKET, "message": ""},
        {**TICKET, "message": "   "},
        {**TICKET, "ticket_id": "bad id with spaces"},
        {**TICKET, "ticket_id": "x" * 65},
        {k: v for k, v in TICKET.items() if k != "customer_id"},
    ],
)
def test_invalid_input_returns_422(api_client_factory, payload):
    client = api_client_factory(respond_with())
    assert client.post("/tickets", json=payload).status_code == 422


def test_configurable_message_size_limit(api_client_factory):
    client = api_client_factory(respond_with(), max_message_chars=50)
    response = client.post("/tickets", json={**TICKET, "message": "a" * 51})
    assert response.status_code == 422
    assert "exceeds 50" in response.json()["detail"]


def test_pii_is_redacted_before_jev_and_database(api_client_factory):
    sent = {}

    def capture(request):
        sent["body"] = json.loads(request.content)
        return httpx2.Response(200, json=wire_response(**CONFIDENT_BILLING))

    client = api_client_factory(capture)
    message = "Refund please. Card 4111 1111 1111 1111, email jane.doe@example.com"
    client.post("/tickets", json={**TICKET, "message": message})

    state_text = sent["body"]["state"]["customer_message"]
    assert "4111" not in state_text and "jane.doe" not in state_text
    assert "[CARD]" in state_text and "[EMAIL]" in state_text

    repo = client.app.state.repository
    assert repo.get("TICKET-001").sanitized_message == state_text


def test_unknown_ticket_returns_404(api_client_factory):
    assert api_client_factory(respond_with()).get("/tickets/NOPE").status_code == 404


def test_list_filters_by_status(api_client_factory):
    client = api_client_factory(respond_with(**CONFIDENT_BILLING))
    client.post("/tickets", json=TICKET)
    assert len(client.get("/tickets", params={"status": "routed"}).json()) == 1
    assert client.get("/tickets", params={"status": "pending_review"}).json() == []
    assert client.get("/tickets", params={"status": "bogus"}).status_code == 422


def test_review_records_human_outcome_and_feeds_metrics(api_client_factory):
    client = api_client_factory(respond_with(**{**CONFIDENT_BILLING, "dept_confidence": 0.3}))
    client.post("/tickets", json=TICKET)
    review = {"reviewer": "agent-7", "final_department": "account", "final_priority": "medium"}
    body = client.post("/tickets/TICKET-001/review", json=review).json()
    assert body["status"] == "reviewed"
    assert body["review_outcome"] == "account/medium by agent-7"

    metrics = client.get("/metrics").json()
    assert metrics["reviewed_tickets"] == 1
    assert metrics["reviewer_agreement"] == 0.0  # model said billing, human said account


def test_metrics_report_coverage_and_errors(api_client_factory):
    responses = iter(
        [
            httpx2.Response(200, json=wire_response(**CONFIDENT_BILLING)),
            httpx2.Response(500, json={}),
        ]
    )
    client = api_client_factory(lambda request: next(responses))
    client.post("/tickets", json=TICKET)
    client.post("/tickets", json={**TICKET, "ticket_id": "TICKET-002"})
    m = client.get("/metrics").json()
    assert m["total_tickets"] == 2
    assert m["automation_coverage"] == 0.5
    assert m["review_rate"] == 0.5
    assert m["inference_error_rate"] == 0.5


def test_health_does_not_call_jev(api_client_factory):
    def must_not_be_called(request):
        raise AssertionError("health check called Jev")

    body = api_client_factory(must_not_be_called).get("/health").json()
    assert body["status"] == "ok" and body["jev_backend"] == "typesafe"


def test_database_failure_returns_503_without_leaking_details(api_client_factory, monkeypatch):
    client = api_client_factory(respond_with(**CONFIDENT_BILLING))

    def broken(*args, **kwargs):
        raise OperationalError("SELECT secret_internal_sql", {}, Exception("disk I/O error"))

    monkeypatch.setattr(client.app.state.repository, "get", broken)
    response = client.post("/tickets", json=TICKET)
    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}
    assert "secret_internal_sql" not in response.text


def test_every_response_carries_a_request_id(api_client_factory):
    client = api_client_factory(respond_with())
    assert client.get("/health").headers["X-Request-ID"]
    assert client.get("/health", headers={"X-Request-ID": "abc"}).headers["X-Request-ID"] == "abc"


def test_openapi_documents_all_endpoints(api_client_factory):
    paths = api_client_factory(respond_with()).get("/openapi.json").json()["paths"]
    assert {
        "/tickets",
        "/tickets/{ticket_id}",
        "/tickets/{ticket_id}/review",
        "/metrics",
        "/health",
    } <= set(paths)


def test_reasons_name_the_human_check_that_fired(api_client_factory):
    client = api_client_factory(
        respond_with(**{**CONFIDENT_BILLING, "human_checks": {"legal_threat": 0.93}})
    )
    body = client.post("/tickets", json=TICKET).json()
    assert body["action"] == "human_review"
    assert body["reasons"] == ["needs_human:legal_threat"]
