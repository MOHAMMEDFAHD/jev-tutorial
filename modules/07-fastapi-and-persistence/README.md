# Module 7 — FastAPI & Persistence

⏱ 50:00–60:00 · ⬅ [Module 6](../06-decision-policy-and-routing/README.md) · Next ➡ [Module 8](../08-testing-and-evaluation/README.md)

**Goal:** expose the pipeline as a REST API with an audit trail, safe retries and human review.

**Slides:** page 16 of [jev-slides.pdf](../01-introduction-and-resources/materials/jev-slides.pdf) ("connect the data source"). ⚠️ Its request JSON
is wrong; the real shape is `{state, model, questions}`.

## Build

| File | What it does |
|---|---|
| [`app/api/routes.py`](../../app/api/routes.py) | `create_ticket()`: size limit → fingerprint → replay/409 → redact → decide → store; dependency injection |
| [`app/main.py`](../../app/main.py) | app factory, lifespan, DB error → 503, anything else → 500 without internals |
| [`app/models/ticket.py`](../../app/models/ticket.py) | request/response schemas |
| [`app/database/`](../../app/database/) | `TicketRecord` audit row, idempotent insert, metrics |

## Run

```bash
uvicorn app.main:app --reload     # Swagger UI: http://127.0.0.1:8000/docs
```

Try, in order: `POST /tickets` (201) → same request again (200, `Idempotent-Replay: true`) →
same id, different text (409) → a 5,000-character message (422) →
`POST /tickets/{id}/review` → `GET /metrics` (`reviewer_agreement`).

Inspect the database: `sqlite3 tickets.db "select ticket_id, department, action, reasons, model from tickets"`.
The stored message is redacted; the full probabilities are kept for audit.

## Status codes

201 new · 200 replay · 409 id reused with different content · 422 invalid input · 503 database unavailable

## Optional

Call this API from a workflow tool: [docs/n8n-integration.md](../../docs/n8n-integration.md) (written, not tested with n8n).

## Common mistake

Without idempotency, a client that retries after a timeout routes the same ticket twice.

## ✅ Checkpoint

You can explain 201 vs 200 vs 409 vs 422 vs 503 for this API.

Next ➡ [Module 8 — Testing & Evaluation](../08-testing-and-evaluation/README.md)
