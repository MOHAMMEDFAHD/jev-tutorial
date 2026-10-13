# Architecture

## Request flow

```text
Client ── POST /tickets ──► api/routes.py
                              │ 1. Pydantic validation (ids, non-blank, size limit)      -> 422
                              │ 2. Idempotency: existing ticket_id?
                              │       same content  -> 200 replay (no new inference)
                              │       other content -> 409
                              │ 3. utils/privacy.redact_pii()
                              ▼
                      services/decision_service.py  (never raises on model failure)
                              │
                              ├─► services/jev_client.py ──► typesafe_sdk.AsyncTypeSafeClient
                              │        one request: state + all questions (questions.py)
                              │        SDK: timeout, retries w/ backoff, Retry-After
                              │        SDK exceptions ──► JevAuthError / JevRateLimitError / ...
                              │
                              ├─► services/decision_parser.py
                              │        native ChoiceAnswer/ScoreAnswer/NoulAnswer
                              │        ──► validated TicketDecision (our enums)  or reject
                              │
                              ├─► policies/automation_policy.py   (Decision D, pure Python)
                              │        -> AUTO_ROUTE | HUMAN_REVIEW + every fired reason
                              │
                              └─► services/routing_service.py     -> queue name
                              ▼
                      database/repository.py ──► SQLite (one row = one audit record)
                              ▼
                      201 TicketResponse  + JSON log line (no ticket text)
```

Any failure between the SDK call and the parser yields `status=inference_failed`,
`action=human_review`, and the failure code as the reason. The ticket is never lost.

## Layers and why they are separate

| Layer | File(s) | Knows about | Does NOT know about |
|---|---|---|---|
| Question design | `services/questions.py` | the SDK's `Choice/Score/Noul` | HTTP, policy, database |
| Inference | `services/jev_client.py` | SDK client, retries, SDK exceptions | our enums, policy |
| Validation | `services/decision_parser.py` | native answers, our enums | thresholds, routing |
| Policy | `policies/automation_policy.py` | `TicketDecision`, thresholds | the SDK, HTTP, DB |
| Routing | `services/routing_service.py` | departments → queues | the SDK |
| Orchestration | `services/decision_service.py` | all of the above | HTTP, DB |
| API | `api/routes.py`, `main.py` | HTTP, DI, idempotency | how Jev works |
| Persistence | `database/*` | SQLAlchemy | the SDK |

Consequences: an SDK upgrade touches `jev_client.py` and `decision_parser.py`; a business-rule
change touches `automation_policy.py`; nothing in `policies/` imports `typesafe_sdk`.

## Native vs. application schema

| Native (TypeSafe SDK) | Application (this repo) |
|---|---|
| `ChoiceAnswer.choice: str` | `Department` enum — unknown labels are rejected |
| `ChoiceAnswer.probabilities: dict[str, float]` | validated: keys == our options, values in [0,1], sum ≈ 1, `choice` is the argmax |
| `ScoreAnswer.score: float` (expected level) | kept as `expected_score`; level = **argmax** of probabilities (TypeSafe advises against interpolating between levels) |
| `ScoreAnswer.probabilities: dict[int, float]` | re-keyed to `Priority` |
| four `NoulAnswer.noul: float` (legal threat, fraud or takeover, compensation, manager request) | `HumanReviewSignal.checks`, plus `probability` = the highest of them (computed by us) |
| — | `top2_margin` (computed), `PolicyOutcome` (policy) |

Verified behaviour of `typesafe-sdk` 0.7.4 that shaped this design:
- the SDK accepts `NaN`, `inf` and `1.5` as `confidence` → our parser checks ranges;
- Score probability keys arrive as strings on the wire and are parsed to `int`;
- `response.request_id` raises `TypeSafeError` when the header is missing → read defensively;
- 408/429/5xx, connection errors and timeouts are retried by the SDK (`RetryPolicy`), honouring `retry-after-ms`.

## Retries and idempotency

Two different retries exist and they must not be confused:

1. **SDK → TypeSafe.** A Jev evaluation has no side effects, so retrying it is always safe.
   We configure the SDK's `RetryPolicy` (max retries + total time budget) rather than writing a loop.
2. **Client → our API.** A client that times out will resend `POST /tickets`. `ticket_id` is the
   primary key, so the second request returns the stored result (200, `Idempotent-Replay: true`)
   without a second inference or a second routing action. A concurrent duplicate that slips past
   the read check hits the primary-key constraint and is converted into the same replay.

## Policy design

```text
                         any rule fires?  ── yes ──► HUMAN_REVIEW (critical → escalation_queue)
business rules           │
  priority ∈ mandatory   │
  P(critical) ≥ limit    │
model's own judgment     │
  any human check ≥ t    │
uncertainty gates        │
  dept confidence < t    │
  top-2 margin < t       │
  priority confidence < t│
                         └─ no ──► AUTO_ROUTE to the department queue
```

All rules are checked and all fired reasons are stored, so reviewers see *why* a ticket was held
and `/metrics` and the evaluation can show which rule drives the review rate.

## Data stored

`ticket_id`, `customer_id`, SHA-256 of the original message (for idempotency checks),
the **redacted** message, department + confidence + full probability distribution, priority
level + expected score + confidence, the four human-review checks and their maximum, model id, TypeSafe request id, input
tokens, latency, action, queue, reasons, status, error reason, and the human review
(reviewer, final department/priority, notes, time). The original message and API keys are
never stored or logged.
