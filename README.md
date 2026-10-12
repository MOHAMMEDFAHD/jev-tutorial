# Practical Jev AI Engineering

**Build production-ready decision systems with Python — from typed probabilistic decisions to real-world AI automation.**

Companion repository for a 60–75 minute hands-on course. You build an **intelligent customer-support
decision engine**: a FastAPI service that classifies, prioritizes and routes support tickets with
**Jev** (TypeSafe AI's System One model), then applies explicit Python business rules to decide
whether each ticket is routed automatically or held for a human.

> **The one idea this course teaches:** *Jev makes the judgment. Your code decides what to do with it.*

## Course modules

**👉 Start with [Module 1](modules/01-introduction-and-resources/README.md)**: it holds the course map,
the slides, and the learning-resources list. Then follow the modules in order; each folder's README
gives the goal, slide pages, reading, files, commands and a ✅ checkpoint.

| # | Module | Time |
|---|---|---|
| 1 | [Introduction, course materials & resources](modules/01-introduction-and-resources/README.md) | 00–05 |
| 2 | [Jev fundamentals](modules/02-jev-fundamentals/README.md) | 05–12 |
| 3 | [Setup & first request](modules/03-setup-and-first-request/README.md) | 12–20 |
| 4 | [Classification with Jev](modules/04-classification-with-jev/README.md) | 20–30 |
| 5 | [Probabilities & validation](modules/05-probabilities-and-validation/README.md) | 30–40 |
| 6 | [Decision policy & routing](modules/06-decision-policy-and-routing/README.md) | 40–50 |
| 7 | [FastAPI & persistence](modules/07-fastapi-and-persistence/README.md) | 50–60 |
| 8 | [Testing & evaluation](modules/08-testing-and-evaluation/README.md) | 60–68 |
| 9 | [Production & next steps](modules/09-production-and-next-steps/README.md) | 68–75 |

---

## Contents

[Course modules](#course-modules) ·
[Jev in 60 seconds](#jev-in-60-seconds) ·
[Where Jev fits](#where-jev-fits-jev-vs-llms-vs-n8n) ·
[What you'll build](#what-youll-build) ·
[Quick start](#quick-start) ·
[Examples](#run-the-examples) ·
[API](#run-the-api) ·
[Tests](#run-the-tests) ·
[Evaluation](#evaluate-decision-quality) ·
[Docker](#docker) ·
[Configuration](#configuration) ·
[Troubleshooting](#troubleshooting) ·
[Course materials](#course-materials) ·
[Resources](#official-resources)

---

## Jev in 60 seconds

Large language models generate text for people. **Jev generates no text at all.** You send it a
**state** (the data to judge) and a set of named, typed **questions**. It returns one typed answer
per question, with probabilities, in a single fast call.

There are three question types (TypeSafe calls them [primitives](https://docs.typesafe.ai/primitives)):

| Primitive | Ask it… | Example | Answer fields |
|---|---|---|---|
| **Choice** | to pick one option from a set (≤ 255) | *Which team should handle this?* | `choice`, `probabilities`, `confidence` |
| **Score** | to rate on ordered levels (2–10) | *How urgent is this?* low → critical | `score`, `probabilities`, `legend`, `confidence` |
| **Noul** | whether a statement is true | *Does this need a human?* | `noul` (probability of yes) |

A real request and the shape of its response:

```json
POST https://api.typesafe.ai/v1/systemone
{
  "state": "I was charged twice for my subscription and need a refund.",
  "model": "jev-latest",
  "questions": {
    "department": {"type": "choice", "instructions": "Which team should handle this?",
                   "criteria": {"billing": "Payments, refunds", "technical": "Bugs, outages",
                                "sales": "Pricing, upgrades"}}
  }
}
```
```json
{
  "model": "jev-1.13.0",
  "answers": {
    "department": {"type": "choice", "choice": "billing",
                   "probabilities": {"billing": 0.88, "technical": 0.12, "sales": 0.0},
                   "confidence": 0.81}
  },
  "usage": {"input_tokens": 318, "output_tokens": 34}
}
```
*(Response values are copied from the example in TypeSafe's [API reference](https://docs.typesafe.ai/api), which used a different message. They show the **shape** of a response, not a result for the request above.)*

Three facts that trip people up:

1. **The answer field is `choice`, keyed by *your* question name.** There is no generic `"decision"` field.
2. **Confidence is not the top probability.** For a Choice with *n* options it is
   `(p_max − 1/n) / (1 − 1/n)`: 0 at an even split, 1 when certain. Probabilities 0.72 / 0.21 / 0.07
   give confidence **0.58**, not 0.72 ([docs](https://docs.typesafe.ai/confidence)). Confidence is
   never a guarantee of correctness.
3. **Jev returns only what you ask.** Want a risk level too? Add a Score question. Want "the amount
   is unusually high"? Compute it in Python and pass the result as a fact. Jev is weak at arithmetic,
   counting and date comparison ([known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13)).

> Using the course slide deck? Slides 16, 17, 19, 22, 23 and 30 simplify these points.
> [docs/slide-companion.md](docs/slide-companion.md) lists each correction, and
> `tests/test_slide_claims.py` verifies them against the real SDK.

## Where Jev fits: Jev vs. LLMs vs. n8n

| | **Jev** | **LLM** | **n8n** |
|---|---|---|---|
| Produces | typed decisions + probabilities | free-form text | workflow actions |
| Best at | classify, route, score, verify, branch | write, explain, summarize | connect apps, trigger steps |
| Output safety | answer is always one of your options | must be parsed and validated | depends on the nodes |
| Speed / cost | TypeSafe states 70–500 ms per call ([launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev)); $0.042 per million input tokens, output free ([models](https://docs.typesafe.ai/models)) | seconds; varies by model | n/a (orchestration) |
| In this project | the decision layer | not used | optional caller ([n8n guide](docs/n8n-integration.md)) |

They're complementary: Jev decides, an LLM writes words when words are needed, and an automation
platform or your own service performs the action.

## What you'll build

```text
POST /tickets ─► validate input ─► redact PII ─► Jev: 1 request, 3 questions in parallel
                                                   department (Choice) · priority (Score) · needs human? (Noul)
                                                          │
                                  typed TicketDecision ◄──┴── validate every answer (reject unknown labels, bad numbers)
                                                          │
                                  automation policy (Python):  business rules → model judgment → confidence gates
                                         │                                        │
                              auto_route → department queue          human_review → review / escalation queue
                                         └────────────► SQLite audit record ◄─────┘ ─► JSON logs · /metrics
```

If Jev is unavailable, slow or returns something invalid, the ticket is **still accepted** and goes
to a human, with the reason recorded.

### From business idea to working system

The deck's "how a business owner can get started" steps (slides 30–31), mapped to this repo:

| Step | What it means | Where it lives here |
|---|---|---|
| 1. Choose one repetitive decision | ticket → department, priority, needs-human | `app/services/questions.py` |
| 2. Connect the data source | an HTTP endpoint any system (website, email, n8n) can call | `POST /tickets` · `app/api/routes.py` |
| 3. Call the Jev API | one request, typed questions, validated answers | `app/services/jev_client.py`, `decision_parser.py` |
| 4. Apply business rules | high confidence → auto; uncertain → review; sensitive → mandatory review | `app/policies/automation_policy.py` |
| 5. Automate the approved action | route to a queue (recorded; wire to your helpdesk) | `app/services/routing_service.py` |
| 6. Measure the results | accuracy, coverage, accuracy on auto-routed tickets, reviewer agreement | `evaluation/evaluate.py`, `GET /metrics` |

### What's official vs. what's ours

The request/response format, the primitives, the confidence formulas, the SDK and its retries and
exceptions are **TypeSafe's**. Everything that decides *what to do* is **application code in this
repo**: thresholds, policy, routing, idempotency, PII redaction, persistence and evaluation.
No threshold here is a TypeSafe recommendation.

## Project structure

```text
app/
  main.py                 FastAPI app factory, lifespan, error handlers
  config.py               all settings from environment variables
  api/routes.py           REST endpoints (thin)
  models/decision.py      app's typed decisions (Department, Priority, TicketDecision…)
  models/ticket.py        HTTP request/response schemas
  services/questions.py   the 3 Jev questions
  services/jev_client.py  SDK wrapper: timeouts, retries, error mapping
  services/decision_parser.py   native Jev answers → validated app types
  services/decision_service.py  the pipeline; never fails because of the model
  services/routing_service.py   decision + action → queue
  services/mock_backend.py      OFFLINE mock (not Jev) for no-key learning and tests
  policies/automation_policy.py Decision D: auto-route or human review
  database/               SQLAlchemy model, session, repository (idempotent insert, metrics)
  utils/                  JSON logging, PII redaction
examples/01–05            progressive, independently runnable scripts
tests/                    98 tests (real SDK, mocked network) + 1 live test
ui/jev_playground.py      local browser playground (Streamlit)
evaluation/               40 labelled synthetic tickets, metrics, evaluate.py
modules/01–09/            one folder per module, in order (Module 1 holds the slides, resources PDF, reading list)
docs/                     course outline, instructor & student guides, slide companion, checklist
```

## Quick start

**Prerequisites:** Python **3.11+**, basic Python/REST/JSON. A TypeSafe API key from the
[console](https://console.typesafe.ai/keys) is optional: everything also runs against a clearly
labelled **offline mock** (its answers are *not* Jev output).

**macOS / Linux**
```bash
git clone <your-fork-url> practical-jev-ai && cd practical-jev-ai
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # then set TYPESAFE_API_KEY=… (or JEV_BACKEND=mock)
pytest -q                   # 98 passed, 1 skipped
```

**Windows (PowerShell)**
```powershell
git clone <your-fork-url> practical-jev-ai; cd practical-jev-ai
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -e ".[dev]"
Copy-Item .env.example .env       # then set TYPESAFE_API_KEY=… (or JEV_BACKEND=mock)
pytest -q
```

`.env` is git-ignored. Never commit it, paste a key into a third-party site, or show it on screen.

## Run the examples

Each runs on its own. Add `--offline` to use the mock instead of the API.

| Script | Module | What it shows |
|---|---|---|
| `python examples/01_first_request.py` | 3 | first authenticated call, raw response, error handling |
| `python examples/02_typed_decisions.py` | 4–5 | Choice / Score / Noul → validated application types |
| `python examples/03_probabilities.py` | 5 | probabilities, confidence (re-computed), margins, thresholds |
| `python examples/04_automated_routing.py` | 6 | the full pipeline over a batch, incl. graceful degradation |
| `python examples/05_business_patterns.py` | 9 | the deck's email, login, invoice and feedback scenarios, built correctly |

## Try it in your browser (playground)

A small local app to type any customer message and see Jev's decision instantly:
the department, priority and "needs a person?" with their probabilities, what the policy
does with them, and why. Policy sliders re-check the last answer without calling Jev again.

```bash
pip install -e ".[ui]"
streamlit run ui/jev_playground.py      # opens http://localhost:8501
```
Run it from the repository root so your `.env` is found. Choose **Live Jev** (uses your key)
or the **offline mock** in the sidebar.

## Run the API

```bash
uvicorn app.main:app --reload       # Swagger UI: http://127.0.0.1:8000/docs
```

```bash
curl -X POST http://127.0.0.1:8000/tickets -H "Content-Type: application/json" \
  -d '{"ticket_id":"TICKET-001","customer_id":"CUSTOMER-100","message":"I was charged twice for my subscription and need a refund."}'
```
```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/tickets -ContentType "application/json" `
  -Body '{"ticket_id":"TICKET-001","customer_id":"CUSTOMER-100","message":"I was charged twice for my subscription and need a refund."}'
```

| Method | Path | Purpose |
|---|---|---|
| POST | `/tickets` | decide + store (201). Same id + same text → 200 replay; same id + different text → 409 |
| GET | `/tickets/{ticket_id}` | the stored decision (audit record) |
| GET | `/tickets?status=pending_review&limit=50&offset=0` | list tickets |
| POST | `/tickets/{ticket_id}/review` | record a human verdict (becomes evaluation data) |
| GET | `/metrics` | automation coverage, review rate, error rate, latency, reviewer agreement |
| GET | `/health` | liveness/readiness (deliberately does not call Jev) |

Response from a run against the **offline mock** (note `"model": "mock-offline"`; with a real key,
`model` is the versioned Jev id):
```json
{"ticket_id": "TICKET-001", "status": "routed", "action": "auto_route", "queue": "billing_queue",
 "department": "billing", "priority": "medium", "requires_human_review": false,
 "confidence": 0.7596, "reasons": ["all_checks_passed"], "model": "mock-offline", "...": "..."}
```

## Run the tests

```bash
pytest -q                                   # 98 tests, no network needed
pytest tests/test_slide_claims.py -v        # the slide-deck corrections, verified
RUN_LIVE_TESTS=1 pytest -m live -s          # 1 contract test against the real API (needs a key)
# PowerShell: $env:RUN_LIVE_TESTS = "1"; pytest -m live -s
ruff format --check . && ruff check .
```
Tests drive the **real** TypeSafe SDK through a mocked network (`httpx2.MockTransport`), so the
SDK's serialization, parsing, retries and exceptions are exercised for real.

## Evaluate decision quality

```bash
python -m evaluation.evaluate                   # backend from .env
python -m evaluation.evaluate --backend mock    # pipeline check only, NOT a Jev measurement
```
It reports department accuracy, per-class precision/recall/F1 and the confusion matrix; priority
accuracy; automation coverage and **accuracy on auto-routed tickets** (the number that matters in
production); calibration (ECE, Brier); error rate; latency; and a threshold sweep. Each report
records the backend and model id.

The 40-ticket dataset is synthetic and small: use it to learn the method, then evaluate on your
own labelled tickets. Any accuracy or time-saving percentages you see in slides are illustrative,
not results from this project.

## Docker

```bash
docker build -t practical-jev-ai .
docker run --rm -p 8000:8000 --env-file .env -v jevdata:/data practical-jev-ai
```

## Configuration

All settings are environment variables (see `.env.example`).

| Variable | Default | Meaning |
|---|---|---|
| `JEV_BACKEND` | `typesafe` | `typesafe` (real API) or `mock` (offline, not Jev) |
| `TYPESAFE_API_KEY` | — | your key |
| `JEV_MODEL` | `jev-latest` | pin a version (e.g. `jev-1.13.0`) before tuning thresholds; aliases move |
| `JEV_TIMEOUT_SECONDS` / `JEV_MAX_RETRIES` / `JEV_RETRY_BUDGET_SECONDS` | 5 / 2 / 10 | per-attempt timeout, SDK retries, total budget |
| `AUTO_ROUTE_MIN_CONFIDENCE` | 0.60 | department confidence needed to auto-route |
| `MIN_TOP2_MARGIN` | 0.15 | minimum gap between the two most likely departments |
| `PRIORITY_MIN_CONFIDENCE` | 0.40 | below this the SLA can't be set reliably |
| `HUMAN_REVIEW_NOUL_THRESHOLD` | 0.50 | P(needs human) at which we escalate |
| `CRITICAL_ESCALATION_PROBABILITY` | 0.25 | P(critical) at which we escalate, even if it isn't the top level |
| `MANDATORY_REVIEW_PRIORITIES` | `["critical"]` | always reviewed, whatever the confidence |
| `MAX_MESSAGE_CHARS` · `REDACT_PII` · `DATABASE_URL` · `LOG_LEVEL` | 4000 · true · sqlite · INFO | limits, privacy, infrastructure |

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `TYPESAFE_API_KEY is not set` at startup | add the key to `.env`, or set `JEV_BACKEND=mock` |
| `TYPESAFE_API_KEY is malformed` | the SDK rejects keys with spaces/control characters; re-copy it |
| every ticket has reason `jev_auth_failed` | key rejected (401/403); regenerate it in the console |
| reason `jev_rate_limited` | still 429 after SDK retries; lower concurrency or request higher limits |
| reason `jev_timeout` / `jev_unavailable` | network/proxy issue or TypeSafe outage; tickets still go to humans |
| reason `decision_validation_failed` | an answer failed our checks; look up `jev_request_id` in the logs |
| offline results look wrong | expected: the mock is a keyword heuristic, not Jev |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: app` | run from the repo root with the venv active |

## Production considerations

This is a **tutorial-quality reference implementation, not a production-certified system**.
[docs/production-checklist.md](docs/production-checklist.md) lists what's implemented and what you
must add before real customer traffic: authentication, Postgres + migrations, a real PII service, an
outbox for downstream actions, and thresholds tuned on your own labelled data.

## Course materials

| Document | For |
|---|---|
| [modules/](modules/README.md) | the course, one folder per module, in order |
| [Module 1 materials](modules/01-introduction-and-resources/README.md#course-materials-in-this-folder) | `jev-slides.pdf`, the resources PDF, and the verified reading list |
| [docs/course-outline.md](docs/course-outline.md) | lesson order, timings, objectives, files, slides |
| [docs/instructor-guide.md](docs/instructor-guide.md) | recording script, module by module |
| [docs/slide-companion.md](docs/slide-companion.md) | how to use `jev-slides.pdf`: slide → module, and the five verbal corrections |
| [docs/student-guide.md](docs/student-guide.md) | self-paced labs, three exercises, final challenge |
| [docs/architecture.md](docs/architecture.md) | design and data flow |
| [docs/n8n-integration.md](docs/n8n-integration.md) | calling this service from n8n |
| [modules/01-introduction-and-resources/learning-resources.md](modules/01-introduction-and-resources/learning-resources.md) | all 48 resource links, verified and mapped to modules |
| [docs/production-checklist.md](docs/production-checklist.md) | what's done and what isn't |

## Official resources

Checked against TypeSafe's [documentation index](https://docs.typesafe.ai/llms.txt) on 11 October 2026.
The full list (48 links, including cookbooks and third-party tutorials) is in
[learning-resources.md](modules/01-introduction-and-resources/learning-resources.md) in Module 1.

| Get started | Concepts | Python SDK | Production |
|---|---|---|---|
| [Website](https://typesafe.ai/) | [System One](https://docs.typesafe.ai/concepts/system-one) | [Install](https://docs.typesafe.ai/sdk/python) | [Known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) |
| [Docs](https://docs.typesafe.ai/) | [Primitives](https://docs.typesafe.ai/primitives) | [Usage](https://docs.typesafe.ai/sdk/python/usage) | [Retries](https://docs.typesafe.ai/sdk/python/api/retries) |
| [Console & keys](https://console.typesafe.ai/) | [Confidence](https://docs.typesafe.ai/confidence) | [Responses](https://docs.typesafe.ai/sdk/python/api/types/responses) | [Confidence-gated routing](https://docs.typesafe.ai/patterns/confidence-routing) |
| [Quick start](https://docs.typesafe.ai/introduction/quickstart) | [State](https://docs.typesafe.ai/concepts/state) | [Exceptions](https://docs.typesafe.ai/sdk/python/api/exceptions) | [Models & limits](https://docs.typesafe.ai/models) |
| [API reference](https://docs.typesafe.ai/api) | [How to build](https://docs.typesafe.ai/concepts/how-to-build-with-system-one) | [SDK source](https://github.com/typesafe-ai/typesafe-sdk-python) | [Changelog](https://docs.typesafe.ai/sdk/python/changelog) |

Tested with `typesafe-sdk` 0.7.4 and the `jev-latest` alias, which pointed to `jev-1.13.0` per the
docs at time of writing. The live API was not reachable from the build environment; run the live
test with your own key to confirm.
