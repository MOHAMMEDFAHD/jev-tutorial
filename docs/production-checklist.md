# Production Readiness Checklist

> **This repository is a tutorial-quality reference implementation. It is not production-certified.**
> It shows sound patterns and is tested, but it has not been load-tested, security-reviewed,
> penetration-tested, or validated on real customer data. Treat the "Not yet" column as required work.

Legend: ✅ implemented and tested · ◐ partially implemented · ❌ not implemented

## Model integration

| Item | Status | Notes |
|---|---|---|
| Official SDK, documented request format | ✅ | `typesafe-sdk` 0.7.4; request shape asserted in `test_jev_client.py` |
| Live API verified with real credentials | ❌ | Not possible while building (no key, no network access to api.typesafe.ai). Run `RUN_LIVE_TESTS=1 pytest -m live -s` before anything else |
| Timeouts | ✅ | per-attempt `JEV_TIMEOUT_SECONDS` + total `JEV_RETRY_BUDGET_SECONDS` |
| Retries with exponential backoff, Retry-After | ✅ | SDK `RetryPolicy`; tested for 429 recovery and exhaustion |
| Error mapping | ✅ | 401/403/400/422/429/5xx/529/timeout/connection/malformed all tested |
| Response validation beyond SDK types | ✅ | enum membership, distribution, argmax, finite ranges |
| Model version pinning | ◐ | configurable (`JEV_MODEL`); default is the moving alias `jev-latest`. **Pin a versioned id before tuning thresholds** |
| Rate-limit-aware concurrency | ◐ | evaluation uses a semaphore; the API relies on SDK retries only — add a client-side limiter at high volume |
| Prompt-injection / adversarial state | ◐ | TypeSafe lists this as a known weakness. Mitigated only by the policy (humans see uncertain cases). Test with your own adversarial set |

## Decision quality

| Item | Status | Notes |
|---|---|---|
| Configurable thresholds | ✅ | environment variables |
| Mandatory business rules beat confidence | ✅ | tested |
| Threshold sweep / calibration report | ✅ | `evaluation/evaluate.py` |
| Thresholds tuned on real labelled data | ❌ | defaults are illustrative. Collect labels via `/tickets/{id}/review` |
| Sufficient evaluation data | ❌ | 40 synthetic tickets is a teaching set, not a validation set |
| Drift monitoring | ◐ | `/metrics` shows review rate & reviewer agreement; no alerting or time windows |
| Option-order bias check | ❌ | jev-1.13 can favour the first Choice option; evaluate with shuffled orders |
| Business impact (response time, manual work saved) | ❌ | slide 31 shows "60% faster / 40% less manual work" as **illustrative** targets. This repo measures accuracy, automation coverage and reviewer agreement only. Measure time-to-first-response and handling time against a baseline before claiming savings |
| Accuracy claims | ◐ | only measured on 40 synthetic tickets; any headline accuracy (e.g. slide 31's 87%) must come from your own labelled data via `evaluation/evaluate.py` |

## API & data

| Item | Status | Notes |
|---|---|---|
| Input validation & size limits | ✅ | ids, blank messages, configurable max length |
| Idempotent ticket creation | ✅ | PK on `ticket_id`, replay/409, race handled |
| Central error handling, no internals leaked | ✅ | DB errors → 503, others → 500 |
| Authentication / authorization | ❌ | **the API is open**. Add API keys/OAuth; restrict `/review` to agents |
| Request rate limiting on our API | ❌ | add at gateway or middleware |
| Database | ◐ | SQLite, single worker. Use Postgres + Alembic migrations for real traffic |
| Downstream actions (ticketing system, notifications) | ❌ | routing is *recorded*, not executed. Use a transactional outbox so actions fire exactly once |
| n8n / workflow-tool integration | ◐ | documented in `docs/n8n-integration.md`; **not tested** with a running n8n. Requires API authentication before any non-local use |
| Re-processing failed inferences | ❌ | `inference_failed` tickets wait for humans; add a retry job if wanted |
| Pagination | ◐ | limit/offset; switch to cursor pagination for large tables |

## Security & privacy

| Item | Status | Notes |
|---|---|---|
| Secrets from environment, never logged | ✅ | `SecretStr`; `.env` git-ignored; tested |
| No message text in logs | ✅ | verified on a running server; SDK logger pinned to WARNING |
| PII redaction before model & DB | ◐ | regex for email/card/phone/long numbers only. Names, addresses etc. pass through. Use a dedicated PII service |
| Data retention policy | ❌ | define how long redacted messages and probabilities are kept; add deletion |
| Data processing agreement with TypeSafe | ❌ | TypeSafe states it does not train on requests; ZDR is offered to enterprise customers — confirm contract terms (docs.typesafe.ai/legal) |
| Non-root container, healthcheck | ✅ written / ❌ built | Dockerfile written but **not built** in the dev environment (Docker unavailable) |
| Dependency pinning / SBOM / scanning | ❌ | ranges in `pyproject.toml`; add a lock file and scanning in CI |

## Operations

| Item | Status | Notes |
|---|---|---|
| Health endpoint | ✅ | DB check; does not spend Jev quota |
| Metrics | ◐ | JSON `/metrics` computed from the DB; export to Prometheus/OpenTelemetry for real monitoring |
| Structured logs with request ids | ✅ | `X-Request-ID` + TypeSafe `jev_request_id` for support tickets |
| Alerting | ❌ | alert on error rate, review-rate spikes, p95 latency |
| CI pipeline | ❌ | run `ruff` + `pytest` on every push |
| Documentation accuracy vs. slide deck | ✅ | five deck simplifications corrected in `docs/slide-companion.md`, each pinned by `tests/test_slide_claims.py` |
| External learning links | ◐ | 41/42 official links matched the official index on 2026-10-11; `cookbooks/basic_memory` not found; 6 third-party links (typesafeai.org) unverified. Re-check periodically |
| Load test | ❌ | not performed |
