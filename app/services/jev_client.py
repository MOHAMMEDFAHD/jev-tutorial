"""Thin wrapper around the official TypeSafe async client.

Responsibilities:
  1. Build the SDK client from settings (key, model, timeout, RetryPolicy).
  2. Send one request with all ticket questions.
  3. Translate SDK exceptions into a few application exceptions so the rest of the app
     never imports typesafe_sdk error classes.

Retries: the SDK already retries 408/429/5xx, connection errors and timeouts with
exponential backoff + jitter and honours Retry-After headers (RetryPolicy). We configure it
rather than writing our own loop. Retrying is safe here because a Jev evaluation has no
side effects; side effects (persisting, routing) happen once, afterwards, guarded by the
ticket_id idempotency key in the repository.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx2
from typesafe_sdk import (
    AsyncTypeSafeClient,
    RetryPolicy,
    SystemOneResponse,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAPIResponseValidationError,
    TypeSafeAPITimeoutError,
    TypeSafeAuthenticationError,
    TypeSafeError,
    TypeSafePermissionDeniedError,
    TypeSafeRateLimitError,
    TypeSafeUnprocessableEntityError,
)

from app.config import Settings
from app.services.questions import build_state, build_ticket_questions


# ---- Application-level errors (what the rest of the app handles) ----------------------
class JevError(Exception):
    """Base class. `reason` is a short machine-readable code safe to store and log."""

    reason = "jev_error"

    def __init__(self, message: str, *, request_id: str | None = None) -> None:
        super().__init__(message)
        self.request_id = request_id


class JevAuthError(JevError):
    reason = "jev_auth_failed"          # bad/missing key: a configuration problem


class JevRateLimitError(JevError):
    reason = "jev_rate_limited"         # still 429 after the SDK's retries


class JevTimeoutError(JevError):
    reason = "jev_timeout"


class JevUnavailableError(JevError):
    reason = "jev_unavailable"          # connection failure or 5xx after retries


class JevBadRequestError(JevError):
    reason = "jev_bad_request"          # 400/422: our question payload is wrong


class JevResponseError(JevError):
    reason = "jev_invalid_response"     # response missing/invalid fields


@dataclass(frozen=True)
class JevResult:
    response: SystemOneResponse
    latency_ms: float


class JevClient:
    """Application-facing Jev client. One instance is shared for the app's lifetime."""

    def __init__(self, sdk_client: AsyncTypeSafeClient, *, backend_name: str = "typesafe") -> None:
        self._sdk = sdk_client
        self.backend_name = backend_name

    async def evaluate_ticket(self, message: str) -> JevResult:
        started = time.perf_counter()
        try:
            response = await self._sdk.system_one(
                state=build_state(message),
                questions=build_ticket_questions(),
            )
        # Order matters: subclasses before their parents.
        except TypeSafeAPIResponseValidationError as exc:
            raise JevResponseError(f"invalid field: {exc.field_path}", request_id=exc.request_id) from exc
        except (TypeSafeAuthenticationError, TypeSafePermissionDeniedError) as exc:
            raise JevAuthError(f"HTTP {exc.status}", request_id=exc.request_id) from exc
        except TypeSafeRateLimitError as exc:
            raise JevRateLimitError("HTTP 429", request_id=exc.request_id) from exc
        except TypeSafeUnprocessableEntityError as exc:
            raise JevBadRequestError("HTTP 422", request_id=exc.request_id) from exc
        except TypeSafeAPIError as exc:
            if 400 <= exc.status < 500:
                raise JevBadRequestError(f"HTTP {exc.status}", request_id=exc.request_id) from exc
            raise JevUnavailableError(f"HTTP {exc.status}", request_id=exc.request_id) from exc
        except TypeSafeAPITimeoutError as exc:
            raise JevTimeoutError("request timed out") from exc
        except TypeSafeAPIConnectionError as exc:
            raise JevUnavailableError("connection failed") from exc
        except TypeSafeError as exc:  # client-side validation, e.g. empty questions
            raise JevBadRequestError(type(exc).__name__) from exc
        latency_ms = (time.perf_counter() - started) * 1000
        return JevResult(response=response, latency_ms=latency_ms)

    async def aclose(self) -> None:
        await self._sdk.aclose()


def build_jev_client(
    settings: Settings, *, transport: httpx2.AsyncBaseTransport | None = None
) -> JevClient:
    """Create the JevClient for the configured backend.

    `transport` lets tests inject an httpx2.MockTransport so the REAL SDK code
    (serialization, parsing, retries, error mapping) runs without network access.
    """
    retry = RetryPolicy(
        max_retries=settings.jev_max_retries,
        timeout=settings.jev_retry_budget_seconds,
    )
    if settings.jev_backend == "mock":
        from app.services.mock_backend import MOCK_API_KEY, MOCK_MODEL_ID, mock_transport

        sdk = AsyncTypeSafeClient(
            api_key=MOCK_API_KEY,
            model=MOCK_MODEL_ID,
            retry=retry,
            timeout=settings.jev_timeout_seconds,
            transport=transport or mock_transport(),
        )
        return JevClient(sdk, backend_name="mock")

    if settings.typesafe_api_key is None:
        raise JevAuthError(
            "TYPESAFE_API_KEY is not set. Add it to .env, or set JEV_BACKEND=mock for offline use."
        )
    try:
        sdk = AsyncTypeSafeClient(
            api_key=settings.typesafe_api_key.get_secret_value(),
            model=settings.jev_model,
            retry=retry,
            timeout=settings.jev_timeout_seconds,
            transport=transport,
        )
    except TypeSafeError as exc:  # the SDK rejects malformed keys before any request
        raise JevAuthError("TYPESAFE_API_KEY is malformed") from exc
    return JevClient(sdk, backend_name="typesafe")
