"""PII redaction and log hygiene."""

import json
import logging

import pytest

from app.utils.logging import JsonFormatter
from app.utils.privacy import content_fingerprint, redact_pii


@pytest.mark.parametrize(
    ("text", "placeholder", "secret"),
    [
        ("mail me at jane.doe+x@example.co.uk", "[EMAIL]", "jane.doe"),
        ("card 4111-1111-1111-1111 failed", "[CARD]", "4111"),
        ("call +1 415-555-0134 now", "[PHONE]", "555-0134"),
        ("account 1234567890123", "[CARD]", "1234567890123"),
    ],
)
def test_common_pii_formats_are_redacted(text, placeholder, secret):
    redacted = redact_pii(text)
    assert placeholder in redacted
    assert secret not in redacted


def test_ordinary_text_is_untouched():
    text = "I was charged twice in March 2026 for 2 seats, error code 500."
    assert redact_pii(text) == text


def test_fingerprint_is_stable_and_not_reversible_text():
    assert content_fingerprint("abc") == content_fingerprint("abc")
    assert content_fingerprint("abc") != content_fingerprint("abd")
    assert "abc" not in content_fingerprint("abc")


def test_json_log_contains_fields_and_no_traceback_text():
    try:
        raise ValueError("customer said: my password is hunter2")
    except ValueError:
        import sys

        record = logging.LogRecord("t", logging.ERROR, __file__, 1, "evt", None, sys.exc_info())
    record.fields = {"ticket_id": "T-1"}
    line = json.loads(JsonFormatter().format(record))
    assert line["ticket_id"] == "T-1" and line["exc_type"] == "ValueError"
    assert "hunter2" not in json.dumps(line)
