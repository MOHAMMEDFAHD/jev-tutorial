# Practical Jev AI Engineering

**Build production-ready decision systems with Python — from typed probabilistic decisions to real-world AI automation.**

This repository is the companion code for a 60–75 minute hands-on course. You build an
**intelligent customer-support decision engine**: a FastAPI service that classifies, prioritizes
and routes support tickets using **Jev**, TypeSafe AI's System One model, and decides with
explicit Python business rules whether each ticket can be routed automatically or must go to a human.

```text
POST /tickets ──► validate ──► redact PII ──► Jev (1 call, 3 typed questions)
                                                │
                     typed TicketDecision ◄── validate answers
                                                │
                              automation policy (Python rules)
                                 │                       │
                          auto-route to queue      human review / escalation
                                 └──────► SQLite audit record ◄──┘ ──► logs & /metrics
```

## What Jev is (and isn't)

Jev is a [System One model](https://docs.typesafe.ai/concepts/system-one): instead of generating
text, it evaluates typed **questions** against a **state** and returns structured answers with
probabilities. Three question types exist ([primitives](https://docs.typesafe.ai/primitives)):

| Type | Use it for | Answer fields |
|---|---|---|
| `Choice` | pick one option from a set (max 255) | `choice`, `probabilities`, `confidence` |
| `Score` | rate on ordered levels (2–10) | `score` (probability-weighted), `probabilities`, `legend`, `confidence` |
| `Noul` | is this statement true? | `noul` — probability of "yes" (no `confidence` field) |

All questions in one request are evaluated in parallel against the same state. Jev cannot
generate text, is weak at arithmetic, counting and date comparison, and reads instructions
literally — see TypeSafe's [jev-1.13 known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

> **What's official vs. what's ours.** The request/response format, the three primitives, the
> `confidence` formulas, the SDK, its retries and exceptions are **TypeSafe's**. Everything that
> decides *what to do* — thresholds, the automation policy, routing, idempotency, PII redaction,
> persistence, evaluation — is **application code in this repo**. No threshold here is a
> TypeSafe recommendation.

## Prerequisites

- Python **3.11+** (the SDK itself supports 3.10+)
- A TypeSafe API key from the [console](https://console.typesafe.ai/keys) — *optional*: everything
  also runs against a clearly labelled **offline mock** (`--offline` / `JEV_BACKEND=mock`)
- Basic Python, REST and JSON knowledge

## Installation

**macOS / Linux**
```bash
git clone <your-fork-url> practical-jev-ai && cd practical-jev-ai
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

**Windows (PowerShell)**
```powershell
git clone <your-fork-url> practical-jev-ai; cd practical-jev-ai
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -e ".[dev]"
Copy-Item .env.example .env
```

## API key configuration

Edit `.env` and set `TYPESAFE_API_KEY=...`. `.env` is git-ignored — never commit it.
No key yet? Set `JEV_BACKEND=mock` in `.env` (offline mock; its answers are **not** Jev output).

## Running the examples

Each example runs on its own. Add `--offline` to use the mock instead of the API.

```bash
python examples/01_first_request.py        # first authenticated request, raw response
python examples/02_typed_decisions.py      # Choice/Score/Noul -> validated app types
python examples/03_probabilities.py        # confidence, margins, thresholds
python examples/04_automated_routing.py    # the full pipeline over a batch of tickets
```

## Running the API

```bash
uvicorn app.main:app --reload
```
Open **http://127.0.0.1:8000/docs** (Swagger UI), or:

```bash
curl -X POST http://127.0.0.1:8000/tickets -H "Content-Type: application/json" \
  -d '{"ticket_id":"TICKET-001","customer_id":"CUSTOMER-100","message":"I was charged twice for my subscription and need a refund."}'
```
PowerShell:
```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/tickets -ContentType "application/json" `
  -Body '{"ticket_id":"TICKET-001","customer_id":"CUSTOMER-100","message":"I was charged twice for my subscription and need a refund."}'
```

| Method | Path | Purpose |
|---|---|---|
| POST | `/tickets` | decide + store a ticket (201; 200 replay for same id+content; 409 for same id, different content) |
| GET | `/tickets/{ticket_id}` | the stored decision (audit record) |
| GET | `/tickets?status=pending_review&limit=50&offset=0` | list tickets |
| POST | `/tickets/{ticket_id}/review` | record a human verdict |
| GET | `/metrics` | coverage, review rate, error rate, latency, reviewer agreement |
| GET | `/health` | liveness/readiness (deliberately does not call Jev) |

Example response (fields as returned by the running service; values depend on the model):
```json
{"ticket_id": "TICKET-001", "status": "routed", "action": "auto_route", "queue": "billing_queue",
 "department": "billing", "priority": "medium", "requires_human_review": false,
 "confidence": 0.7596, "reasons": ["all_checks_passed"], "model": "mock-offline", ...}
```
*(That output came from the offline mock — note `"model": "mock-offline"`. With a real key,
`model` reports the versioned Jev id, e.g. `jev-1.13.0`.)*

## Running the tests

```bash
pytest                                          # 87 tests, no network needed
RUN_LIVE_TESTS=1 pytest -m live -s              # 1 contract test against the real API (needs key)
ruff format --check . && ruff check .           # formatting + lint
```
The tests use the **real** TypeSafe SDK with a mocked network (`httpx2.MockTransport`), so the
SDK's serialization, parsing, retries and exceptions are exercised for real.

## Evaluating predictions

```bash
python -m evaluation.evaluate                  # uses JEV_BACKEND from .env
python -m evaluation.evaluate --backend mock   # pipeline check only - NOT a Jev measurement
```
Reports department accuracy, per-class precision/recall/F1, confusion matrix, priority accuracy,
automation coverage, **accuracy on auto-routed tickets**, calibration (ECE, Brier), error rate,
latency, and a threshold sweep. Reports are saved to `evaluation/results/` with the backend and
model id recorded. The 40-ticket dataset is synthetic and small: use it to learn the method, then
evaluate on your own labelled data.

## Docker

```bash
docker build -t practical-jev-ai .
docker run --rm -p 8000:8000 --env-file .env -v jevdata:/data practical-jev-ai
```

## Configuration reference

All settings are environment variables (see `.env.example`). Policy thresholds:

| Variable | Default | Meaning |
|---|---|---|
| `AUTO_ROUTE_MIN_CONFIDENCE` | 0.60 | department confidence needed to auto-route |
| `MIN_TOP2_MARGIN` | 0.15 | min gap between the two most likely departments |
| `PRIORITY_MIN_CONFIDENCE` | 0.40 | below this the SLA can't be set reliably |
| `HUMAN_REVIEW_NOUL_THRESHOLD` | 0.50 | P(needs human) at which we escalate |
| `CRITICAL_ESCALATION_PROBABILITY` | 0.25 | P(critical) at which we escalate, even if not the top level |
| `MANDATORY_REVIEW_PRIORITIES` | `["critical"]` | always reviewed, regardless of confidence |

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `TYPESAFE_API_KEY is not set` at startup | add the key to `.env`, or set `JEV_BACKEND=mock` |
| `TYPESAFE_API_KEY is malformed` | the SDK rejects keys with spaces/control characters - re-copy it |
| every ticket has reason `jev_auth_failed` | key rejected (401/403) - regenerate it in the console |
| reason `jev_rate_limited` | still 429 after SDK retries - lower concurrency or request higher limits |
| reason `jev_timeout` / `jev_unavailable` | network/proxy issue or TypeSafe outage; tickets still go to humans |
| reason `decision_validation_failed` | the answer failed our checks (e.g. unexpected label) - inspect logs by `jev_request_id` |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: app` | run commands from the repo root with the venv active |

## Production considerations

This is a **tutorial-quality reference implementation, not a production-certified system**.
See [docs/production-checklist.md](docs/production-checklist.md) for what is implemented and what
you must add before real customer traffic (auth, Postgres + migrations, a real PII service,
an outbox for downstream actions, threshold tuning on your own data, …).

## Course materials

- [docs/course-outline.md](docs/course-outline.md) — lesson order, timings, objectives, files
- [docs/instructor-guide.md](docs/instructor-guide.md) — recording script per module
- [docs/student-guide.md](docs/student-guide.md) — self-paced lab, exercises, final challenge
- [docs/architecture.md](docs/architecture.md) — design and data flow
- [docs/production-checklist.md](docs/production-checklist.md)

## Official resources (verified October 2026)

- Docs: https://docs.typesafe.ai/introduction · API reference: https://docs.typesafe.ai/api
- Python SDK: https://docs.typesafe.ai/sdk/python · source: https://github.com/typesafe-ai/typesafe-sdk-python
- Confidence: https://docs.typesafe.ai/confidence · Models, limits, pricing: https://docs.typesafe.ai/models
- Announcement: https://typesafe.ai/blog/introducing-system-one-models-and-jev
- Console & keys: https://console.typesafe.ai/

Tested with `typesafe-sdk` 0.7.4 and model alias `jev-latest` → `jev-1.13.0` (per the docs at time of writing).
