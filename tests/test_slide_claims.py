"""Executable checks for statements made about the course slide deck (docs/slide-companion.md).

Each test pins one claim so the companion doc can't drift from the real SDK/API.
"""

import json

import httpx2
import pytest
from typesafe_sdk import Choice, Score, TypeSafeClient

from app.services.mock_backend import MOCK_API_KEY, mock_transport


def choice_confidence(probabilities: list[float]) -> float:
    """TypeSafe's documented Choice formula (docs.typesafe.ai/confidence)."""
    n = len(probabilities)
    return (max(probabilities) - 1 / n) / (1 - 1 / n)


def test_slide10_python_snippet_runs_against_the_real_sdk():
    """Slide 10's code, verbatim except for the offline transport, is valid SDK usage."""
    with TypeSafeClient(api_key=MOCK_API_KEY, transport=mock_transport()) as client:
        result = client.system_one(
            state="My order has not arrived",
            questions={
                "route": Choice(
                    instructions="Which team?",
                    criteria={"shipping": "Delivery issues", "billing": "Payment issues"},
                )
            },
        )
    assert result.choices["route"].choice in {"shipping", "billing"}


def test_slides_8_and_9_confidence_is_not_the_top_probability():
    """Slides 8-9 show fraud 0.72 / legit 0.21 / review 0.07 with 'confidence 0.72'.
    Under TypeSafe's formula that distribution has confidence ~0.58."""
    assert choice_confidence([0.72, 0.21, 0.07]) == pytest.approx(0.58)


def test_slide11_two_option_vs_three_option_confidence():
    """Confidence depends on the number of options: 0.92 top probability among 3 options."""
    assert choice_confidence([0.92, 0.06, 0.02]) == pytest.approx(0.88)


def test_real_request_body_shape_differs_from_slide16():
    """Slide 16 shows {question, choices, input}. The SDK sends {state, model, questions}."""
    sent = {}

    def capture(request: httpx2.Request) -> httpx2.Response:
        sent.update(json.loads(request.content))
        return mock_transport().handle_request(request)

    with TypeSafeClient(api_key=MOCK_API_KEY, transport=httpx2.MockTransport(capture)) as client:
        client.system_one(
            state="I have a billing issue with my order.",
            questions={
                "category": Choice(
                    instructions="Which category does this message belong to?",
                    criteria={"billing": None, "shipping": None, "technical": None},
                )
            },
        )
    assert set(sent) == {"state", "model", "questions"}
    assert sent["questions"]["category"]["type"] == "choice"
    assert not {"question", "choices", "input"} & set(sent)


def test_answers_contain_only_what_was_asked():
    """Slide 9 shows reason_code / risk_level. Jev returns one answer per question you
    ask, so extra fields require extra questions (here: a Score for risk level)."""
    with TypeSafeClient(api_key=MOCK_API_KEY, transport=mock_transport()) as client:
        result = client.system_one(
            state={"merchant": "Online Store", "amount_above_customer_p95": True},
            questions={
                "verdict": Choice(
                    instructions="Classify this transaction.",
                    criteria={"fraud": None, "legit": None, "review": None},
                ),
                "risk_level": Score(
                    instructions="How risky is this transaction?",
                    criteria=["low", "medium", "high"],
                ),
            },
        )
    assert set(result.answers) == {"verdict", "risk_level"}
    assert not hasattr(result.answers["verdict"], "reason_code")
