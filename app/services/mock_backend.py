"""OFFLINE MOCK of the TypeSafe /v1/systemone endpoint.  *** NOT JEV. NOT MODEL OUTPUT. ***

Why it exists:
  * Learners without an API key can still run the app, the examples and the tests.
  * Tests need deterministic responses and controllable failures.

How it works:
  It is an httpx2.MockTransport plugged into the REAL `AsyncTypeSafeClient`. It answers
  in the documented wire format (docs.typesafe.ai/api), so the official SDK still performs
  serialization, response parsing, validation and retries. The "predictions" come from a
  crude keyword heuristic and the confidences use TypeSafe's published formulas
  (docs.typesafe.ai/confidence) applied to those made-up probabilities.

Every response reports model="mock-offline" so mock results are visible in the API
response, the database, the metrics, and evaluation reports. Never present them as Jev.

Failure simulation (mock only): put one of these markers in the message text
  [[simulate:429]]  [[simulate:500]]  [[simulate:401]]  [[simulate:timeout]]  [[simulate:malformed]]
"""

from __future__ import annotations

import json
import re

import httpx2

MOCK_MODEL_ID = "mock-offline"
MOCK_API_KEY = "mock-offline-key"

_KEYWORDS: dict[str, list[str]] = {
    "billing": ["charge", "charged", "refund", "invoice", "payment", "billing", "card", "receipt"],
    "technical": ["error", "bug", "crash", "down", "outage", "api", "integration", "slow", "500"],
    "account": [
        "password",
        "login",
        "log in",
        "locked",
        "2fa",
        "two-factor",
        "hacked",
        "cancel",
        "email address",
        "account",
    ],
    "sales": ["pricing", "price", "quote", "upgrade", "enterprise", "plan", "seats", "demo"],
}
_URGENT = ["asap", "urgent", "immediately", "blocked", "losing", "today", "cannot", "can't"]
_CRITICAL = ["hacked", "breach", "data loss", "deleted all", "outage", "everyone", "all users"]
_HUMAN = ["lawyer", "legal", "sue", "manager", "fraud", "compensation", "chargeback", "hacked"]
_SIM = re.compile(r"\[\[simulate:(\w+)\]\]")


def _choice_confidence(probabilities: list[float]) -> float:
    """TypeSafe's documented Choice formula: (p_max - 1/n) / (1 - 1/n)."""
    n = len(probabilities)
    return round((max(probabilities) - 1 / n) / (1 - 1 / n), 4)


def _score_confidence(probabilities: list[float]) -> float:
    """TypeSafe's documented Score formula (probability-weighted distance from the peak)."""
    n = len(probabilities)
    m = probabilities.index(max(probabilities))
    spread = sum(p * abs(i - m) for i, p in enumerate(probabilities))
    even_spread = sum(abs(i - (n - 1) / 2) for i in range(n)) / n
    return round(max(0.0, 1 - spread / even_spread), 4)


def _hits(text: str, words: list[str]) -> int:
    return sum(1 for w in words if w in text)


def _department_answer(text: str, options: list[str]) -> dict:
    weights = {opt: 0.3 + 2.0 * _hits(text, _KEYWORDS.get(opt, [])) for opt in options}
    if "general" in weights:
        weights["general"] = 0.6  # weak default
    total = sum(weights.values())
    probs = {k: round(v / total, 4) for k, v in weights.items()}
    choice = max(probs, key=probs.get)
    return {
        "type": "choice",
        "choice": choice,
        "probabilities": probs,
        "confidence": _choice_confidence(list(probs.values())),
    }


def _priority_answer(text: str, legend: list) -> dict:
    n = len(legend)
    level = min(
        n - 1, 1 + (1 if _hits(text, _URGENT) else 0) + (1 if _hits(text, _CRITICAL) else 0)
    )
    if level == 1 and _hits(text, ["question", "wondering", "curious", "how do i"]):
        level = 0
    probs = [0.04] * n
    probs[level] = 1 - 0.04 * (n - 1)
    return {
        "type": "score",
        "score": round(sum(i * p for i, p in enumerate(probs)), 4),
        "confidence": _score_confidence(probs),
        "legend": {str(i): str(d) for i, d in enumerate(legend)},
        "probabilities": {str(i): round(p, 4) for i, p in enumerate(probs)},
    }


def _noul_answer(text: str) -> dict:
    return {"type": "noul", "noul": 0.9 if _hits(text, _HUMAN) else 0.08}


def _answer(question: dict, text: str) -> dict:
    kind = question.get("type")
    if kind == "choice":
        return _department_answer(text, list(question["criteria"]))
    if kind == "score":
        return _priority_answer(text, list(question["criteria"]))
    return _noul_answer(text)


def handle_request(request: httpx2.Request) -> httpx2.Response:
    headers = {"x-typesafe-request-id": "mock-request"}
    if request.url.path.endswith("/v1/models"):
        return httpx2.Response(
            200,
            headers=headers,
            json={
                "models": [
                    {
                        "name": MOCK_MODEL_ID,
                        "description": "Offline keyword mock (not Jev)",
                        "release_date": "2026-01-01",
                    }
                ]
            },
        )

    body = json.loads(request.content)
    text = json.dumps(body["state"]).lower()

    simulated = _SIM.search(text)
    if simulated:
        mode = simulated.group(1)
        if mode == "timeout":
            raise httpx2.ReadTimeout("simulated timeout", request=request)
        if mode in {"429", "500", "401"}:
            return httpx2.Response(int(mode), headers=headers, json={"detail": f"simulated {mode}"})
        if mode == "malformed":
            return httpx2.Response(
                200,
                headers=headers,
                json={
                    "model": MOCK_MODEL_ID,
                    "usage": {},
                    "answers": {"department": {"type": "choice"}},
                },
            )

    answers = {key: _answer(q, text) for key, q in body["questions"].items()}
    return httpx2.Response(
        200,
        headers=headers,
        json={
            "model": MOCK_MODEL_ID,
            "answers": answers,
            "usage": {"input_tokens": len(text) // 4, "output_tokens": 0},
        },
    )


def mock_transport() -> httpx2.MockTransport:
    return httpx2.MockTransport(handle_request)
