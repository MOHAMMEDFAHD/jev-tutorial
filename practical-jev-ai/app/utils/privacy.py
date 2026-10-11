"""Minimal PII redaction, applied BEFORE text is sent to Jev or written to the database.

This is a teaching-grade, regex-based filter. It catches common formats (emails, card-like
numbers, phone numbers, long digit runs) and will miss others (names, addresses, free-form
identifiers). Production systems should use a dedicated PII service and a data-retention policy.
The department/priority decisions do not need these details, so removing them costs nothing.
"""

import hashlib
import re

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("[EMAIL]", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("[CARD]", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("[PHONE]", re.compile(r"(?<!\w)\+?\d{1,3}?[ .-]?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}\b")),
    ("[NUMBER]", re.compile(r"\b\d{9,}\b")),
]


def redact_pii(text: str) -> str:
    for placeholder, pattern in _PATTERNS:
        text = pattern.sub(placeholder, text)
    return text


def content_fingerprint(text: str) -> str:
    """Stable hash of the ORIGINAL message, used to detect idempotency-key reuse
    with different content without storing the original text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
