# Using this service from n8n

Slides 18–20 contrast Jev (decisions) with n8n (workflow automation), and slide 30 lists n8n as a
way to connect data sources. They work best **together**: n8n moves data and performs actions;
this service makes the typed decision **and applies your business policy**. n8n then branches on
the policy's `action` instead of re-implementing thresholds in a workflow.

```text
[Trigger: email / form / webhook] ──► [HTTP Request: POST /tickets] ──► [Switch on action]
                                                                         ├─ auto_route   → assign team (CRM / helpdesk)
                                                                         └─ human_review → notify reviewers (Slack / email)
```

> **Status:** written from n8n's standard HTTP Request and Switch nodes; **not tested** in the
> course environment (n8n wasn't available). Field names in the response are verified against this
> repo's API tests.

## Why call this service rather than the Jev API directly from n8n?

You *can* call `https://api.typesafe.ai/v1/systemone` from an HTTP Request node. You'd then have to
rebuild, inside n8n, everything this repo adds: response validation, the confidence policy,
mandatory-review rules, graceful degradation, idempotency, PII redaction and the audit record.
Calling `POST /tickets` keeps one tested source of truth for the policy.

## Setup

1. Run the service where n8n can reach it (same Docker network or private host):
   `docker run --rm -p 8000:8000 --env-file .env -e DATABASE_URL=sqlite:////data/tickets.db -v jevdata:/data practical-jev-ai`
2. **Do not expose it publicly as-is** — the API has no authentication yet (see
   [production-checklist.md](production-checklist.md)). Put it behind a gateway with an API key
   before any internet exposure.

## Node 1 — HTTP Request

| Setting | Value |
|---|---|
| Method | `POST` |
| URL | `http://<service-host>:8000/tickets` |
| Body content type | JSON |
| Body | see below |

```json
{
  "ticket_id": "{{ $json.ticket_id }}",
  "customer_id": "{{ $json.customer_id }}",
  "message": "{{ $json.message }}"
}
```

Map those three fields from your trigger. `ticket_id` must be **stable for the same message**
(e.g. the email's Message-ID, sanitized to letters, digits, `-`, `_`, max 64 chars).
That makes it safe to enable n8n's *Retry On Fail*: a retried request returns the stored decision
(HTTP 200, header `Idempotent-Replay: true`) instead of creating a second routing action.

## Node 2 — Switch on `{{ $json.action }}`

| Value | Branch |
|---|---|
| `auto_route` | assign to the team in `{{ $json.queue }}` (e.g. `billing_queue`) |
| `human_review` | notify reviewers; include `{{ $json.reasons }}` so they know why it was held |

Useful response fields: `department`, `priority`, `confidence`, `reasons`, `status`
(`inference_failed` means Jev was unavailable — the ticket still arrives, routed to humans),
and `model` (which model version decided).

## Closing the loop

When a reviewer resolves a held ticket, have n8n call:

```http
POST /tickets/{ticket_id}/review
{"reviewer": "agent-7", "final_department": "billing", "final_priority": "high"}
```

Those verdicts are your labelled data: `GET /metrics` reports `reviewer_agreement`, and you can
export them to re-run `evaluation/evaluate.py` on real tickets (slide 31, step 6).

## Status codes to handle in n8n

| Code | Meaning | n8n handling |
|---|---|---|
| 201 | new ticket decided | continue |
| 200 | replay of an existing ticket | continue (same result) |
| 409 | same `ticket_id`, different message | fix the id mapping — don't retry |
| 422 | invalid input (bad id, empty or too-long message) | route to an error branch |
| 503 | database unavailable | retry with backoff |
