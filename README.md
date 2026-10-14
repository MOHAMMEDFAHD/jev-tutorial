# Practical Jev AI Engineering

**Build production-ready decision systems with Python: from typed probabilistic decisions to real-world AI automation.**

A hands-on course and companion repository. You build an **intelligent customer-support decision engine**:
a FastAPI service that classifies, prioritizes and routes support tickets with **Jev** (TypeSafe AI's
System One model), then applies explicit Python business rules to decide whether each ticket is routed
automatically or held for a person.

> **The one idea this course teaches:** *Jev makes the judgment. Your code decides what to do with it.*

**Verified live** against `jev-1.13.0` with `typesafe-sdk` 0.7.4 · **103 automated tests** · FastAPI · SQLite · Docker · a browser playground

---

## Contents

[Course modules](#course-modules) ·
[Jev in 60 seconds](#jev-in-60-seconds) ·
[Where Jev fits](#where-jev-fits-jev-vs-llms-vs-n8n) ·
[What you'll build](#what-youll-build) ·
[Project structure](#project-structure) ·
[Quick start](#quick-start) ·
[Examples](#run-the-examples) ·
[Playground](#try-it-in-your-browser-playground) ·
[API](#run-the-api) ·
[Tests](#run-the-tests) ·
[Evaluation](#evaluate-decision-quality) ·
[Docker](#docker) ·
[Configuration](#configuration) ·
[Troubleshooting](#troubleshooting) ·
[Course materials](#course-materials) ·
[Resources](#official-resources)

---

## Course modules

**👉 Start with [Module 1](modules/01-introduction-and-resources/README.md)**: it holds the course map,
the slides and the learning-resources list. Then follow the modules in order. Each folder's README gives
the goal, slide pages, reading, files, commands and a ✅ checkpoint.

| # | Module | You leave with |
|---|---|---|
| 1 | [Introduction, course materials & resources](modules/01-introduction-and-resources/README.md) | the map, the slides, the ideas behind Jev (Kahneman, Jevons) |
| 2 | [Jev fundamentals](modules/02-jev-fundamentals/README.md) | state, questions, Choice / Score / Noul, confidence |
| 3 | [Setup & first request](modules/03-setup-and-first-request/README.md) | an API key, a working environment, Jev's first answer |
| 4 | [Classification with Jev](modules/04-classification-with-jev/README.md) | the ticket questions and a reliable Jev client |
| 5 | [Probabilities & validation](modules/05-probabilities-and-validation/README.md) | typed, validated decisions |
| 6 | [Decision policy & routing](modules/06-decision-policy-and-routing/README.md) | business rules, queues, human review |
| 7 | [FastAPI & persistence](modules/07-fastapi-and-persistence/README.md) | a REST API with an audit trail |
| 8 | [Testing & evaluation](modules/08-testing-and-evaluation/README.md) | a tested pipeline and measured quality |
| 9 | [Production & next steps](modules/09-production-and-next-steps/README.md) | privacy, logging, Docker, the playground |

📄 Every command in the course, in order, with expected results: **[docs/command-reference.pdf](docs/command-reference.pdf)**

---

## Jev in 60 seconds

Large language models generate text for people. **Jev generates no text at all.** You send it a
**state** (the data to judge) and a set of named, typed **questions**. It returns one typed answer per
question, with probabilities, in a single fast call.

There are three question types (TypeSafe calls them [primitives](https://docs.typesafe.ai/primitives)):

| Primitive | Ask it… | Example | Answer fields |
|---|---|---|---|
| **Choice** | to pick one option from a set (≤ 255) | *Which team should handle this?* | `choice`, `probabilities`, `confidence` |
| **Score** | to rate on ordered levels (2–10) | *How urgent is this?* low → critical | `score`, `probabilities`, `legend`, `confidence` |
| **Noul** | whether a statement is true | *Is there a legal threat?* | `noul` (probability of yes) |

A request, and the shape of a response:

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
*(Response values are copied from the example in TypeSafe's [API reference](https://docs.typesafe.ai/api), which used a different message. They show the **shape** of a response.)*

Three facts that trip people up:

1. **The answer field is `choice`, keyed by *your* question name.** There is no generic `"decision"` field.
2. **Confidence is not the top probability.** For a Choice with *n* options it is
   `(p_max − 1/n) / (1 − 1/n)`: 0 at an even split, 1 when certain. Probabilities 0.72 / 0.21 / 0.07
   give confidence **0.58**, not 0.72 ([docs](https://docs.typesafe.ai/confidence)). Confidence is never
   a guarantee of correctness.
3. **Jev returns only what you ask.** Want a risk level too? Add a Score question. Want "the amount is
   unusually high"? Compute it in Python and pass the result as a fact. Jev is weak at arithmetic,
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
| Speed / cost | TypeSafe states 70–500 ms per call ([launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev)); in our runs, typically about 250 ms. $0.042 per million input tokens, output free ([models](https://docs.typesafe.ai/models)) | seconds; varies by model | n/a (orchestration) |
| In this project | the decision layer | not used | optional caller ([n8n guide](docs/n8n-integration.md)) |

They're complementary: Jev decides, an LLM writes words when words are needed, and an automation
platform or your own service performs the action.

## What you'll build

```text
POST /tickets ─► validate input ─► redact PII ─► Jev: 1 request, all questions in parallel
                                                   department (Choice) · priority (Score) · needs a person? (4 Noul checks)
                                                          │
                                  typed TicketDecision ◄──┴── validate every answer (reject unknown labels, bad numbers)
                                                          │
                                  automation policy (Python):  business rules → the four checks → confidence gates
                                         │                                        │
                              auto_route → department queue          human_review → review / escalation queue
                                         └────────────► SQLite audit record ◄─────┘ ─► JSON logs · /metrics
```

The app makes **three decisions** per ticket. The third, *does this need a person?*, is answered by
**four narrow yes/no checks** (legal threat, fraud or account takeover, compensation request, manager
request). Our code sends the ticket to a person if **any** of them is likely, and the reasons name
exactly which one fired, e.g. `needs_human:legal_threat`.

If Jev is unavailable, slow or returns something invalid, the ticket is **still accepted** and goes to a
person, with the reason recorded (`jev_timeout`, `jev_auth_failed`, …).

### From business idea to working system

The deck's "how a business owner can get started" steps (slides 30–31), mapped to this repo:

| Step | What it means | Where it lives here |
|---|---|---|
| 1. Choose one repetitive decision | ticket → department, priority, needs a person | `app/services/questions.py` |
| 2. Connect the data source | an HTTP endpoint any system (website, email, n8n) can call | `POST /tickets` · `app/api/routes.py` |
| 3. Call the Jev API | one request, typed questions, validated answers | `app/services/jev_client.py`, `decision_parser.py` |
| 4. Apply business rules | high confidence → auto; uncertain → review; sensitive → mandatory review | `app/policies/automation_policy.py` |
| 5. Automate the approved action | route to a queue (recorded; wire to your helpdesk) | `app/services/routing_service.py` |
| 6. Measure the results | accuracy, coverage, accuracy on auto-routed tickets, reviewer agreement | `evaluation/evaluate.py`, `GET /metrics` |

### What's official vs. what's ours

The request/response format, the primitives, the confidence formulas, the SDK and its retries and
exceptions are **TypeSafe's**. Everything that decides *what to do* is **application code in this repo**:
thresholds, policy, routing, idempotency, PII redaction, persistence and evaluation. No threshold here is
a TypeSafe recommendation.

## Project structure

```text
app/
  main.py                       FastAPI app factory: startup, request logging, error handling
  config.py                     all settings from environment variables / .env
  api/routes.py                 REST endpoints (thin)
  models/decision.py            the app's typed decisions (Department, Priority, TicketDecision…)
  models/ticket.py              HTTP request/response schemas
  services/questions.py         the questions: Choice + Score + four Noul checks
  services/jev_client.py        SDK wrapper: timeouts, retries, error mapping
  services/decision_parser.py   native Jev answers → validated app types (or rejected)
  services/decision_service.py  the pipeline; never fails because of the model
  services/routing_service.py   decision + action → queue
  services/mock_backend.py      OFFLINE mock (not Jev) for no-key learning and tests
  policies/automation_policy.py auto-route or a person, with every reason
  database/                     SQLAlchemy model, session, repository (duplicate-safe insert, metrics)
  utils/                        JSON logging, PII redaction
ui/jev_playground.py            browser playground (Streamlit)
examples/01–05                  progressive, independently runnable scripts
tests/                          103 tests (real SDK, mocked network) + 1 live test
evaluation/                     40 labelled synthetic tickets, metrics, evaluate.py
modules/01–09/                  the course, one folder per module (Module 1 holds the slides & resources)
docs/                           command reference (PDF), outline, guides, slide companion, checklist
Dockerfile                      production-style container (non-root, health check)
```

## Quick start

**You need:** Python **3.11+**, Git, and basic Python/REST/JSON. A TypeSafe API key from the
[console](https://console.typesafe.ai/keys) is optional: everything also runs against a clearly
labelled **offline mock** (its answers are *not* Jev output). A full course run costs a fraction of a cent.

**Windows (PowerShell, e.g. VS Code's terminal: Ctrl + `)**
```powershell
git clone https://github.com/MOHAMMEDFAHD/jev-tutorial.git
cd jev-tutorial
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -e ".[dev,ui]"
Copy-Item .env.example .env       # then set TYPESAFE_API_KEY=… in .env
pytest -q                         # 103 passed, 1 skipped
python examples/01_first_request.py
```

**macOS / Linux / Git Bash**
```bash
git clone https://github.com/MOHAMMEDFAHD/jev-tutorial.git
cd jev-tutorial
python3 -m venv .venv
source .venv/bin/activate         # Git Bash on Windows: source .venv/Scripts/activate
pip install -e ".[dev,ui]"
cp .env.example .env              # then set TYPESAFE_API_KEY=… in .env
pytest -q                         # 103 passed, 1 skipped
python examples/01_first_request.py
```

**VS Code tips**
- If a blue bar says **Restricted Mode**, click **Manage → Trust** the folder.
- **Ctrl + Shift + P → Python: Select Interpreter → `.venv`**, so imports resolve.
- Use **VS Code's terminal** for everything. Don't mix in "Run as administrator" windows (see Troubleshooting).
- `.env` is git-ignored. Never commit it, never show it on screen, never paste your key into a chat or a third-party site.

Check your key is being read, without printing it:
```powershell
python -c "from app.config import Settings; print('key found:', Settings().typesafe_api_key is not None)"
```

## Run the examples

Each runs on its own. Add `--offline` to use the mock instead of the API.

| Script | Module | What it shows |
|---|---|---|
| `python examples/01_first_request.py` | 3 | first authenticated call, raw response, error handling |
| `python examples/02_typed_decisions.py` | 4–5 | Choice / Score / four Nouls → validated application types; a tampered answer rejected |
| `python examples/03_probabilities.py` | 5 | probabilities, confidence (re-computed), margins, the same answers under three policies |
| `python examples/04_automated_routing.py` | 6 | the full pipeline on six tickets; `--offline` adds a simulated timeout |
| `python examples/05_business_patterns.py` | 9 | the deck's email, login, invoice and feedback scenarios: facts in code, judgment in Jev |

## Try it in your browser (playground)

Type any customer message and see Jev's decision in under a second: the department, priority and the four
"needs a person?" checks with their probabilities, what the policy does with them, and **why**. Policy
sliders re-check the last answer **without calling Jev again**.

```bash
streamlit run ui/jev_playground.py      # opens http://localhost:8501 (first run: press Enter at the email prompt)
```
Run it from the repository root so your `.env` is found. Choose **Live Jev** or the **offline mock** in the
sidebar. Stop it with Ctrl + C.

## Run the API

```bash
uvicorn app.main:app --reload       # Swagger UI: http://127.0.0.1:8000/docs
```

| Method | Path | Purpose |
|---|---|---|
| POST | `/tickets` | decide + store (201). Same id + same text → 200 replay; same id + different text → 409; bad input → 422 |
| GET | `/tickets/{ticket_id}` | the stored decision (audit record) |
| GET | `/tickets?status=pending_review&limit=50&offset=0` | list tickets |
| POST | `/tickets/{ticket_id}/review` | record a person's verdict (becomes evaluation data) |
| GET | `/metrics` | automation coverage, review rate, error rate, latency, reviewer agreement |
| GET | `/health` | liveness/readiness (deliberately does not call Jev) |

Try these bodies in Swagger (**POST /tickets → Try it out → Execute**):

```json
{"ticket_id": "T-200", "customer_id": "C-10", "message": "I forgot my password and the reset email never arrived."}
```
```json
{"ticket_id": "T-201", "customer_id": "C-11", "message": "My account was hacked and someone changed my email. I'm calling my lawyer and I want to speak to your manager."}
```
The first is routed automatically to the account queue. The second goes to the **escalation queue**, with
reasons such as `mandatory_review_priority`, `needs_human:legal_threat`, `needs_human:fraud_or_takeover`
and `needs_human:manager_request`. Then record a review:

```json
{"reviewer": "agent-1", "final_department": "account", "final_priority": "critical", "notes": "Confirmed account takeover"}
```

From a terminal instead of Swagger:
```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/tickets -ContentType "application/json" `
  -Body '{"ticket_id":"T-300","customer_id":"C-1","message":"Do you offer a discount for 50 seats?"}'
```
```bash
curl -X POST http://127.0.0.1:8000/tickets -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-301","customer_id":"C-1","message":"The export button gives an error."}'
```

While the server runs, its terminal prints one **JSON log line** per event (`ticket_decided`,
`http_request`, …) with ids, decisions, reasons and timings, but never the message text or personal data.

Look inside the database (personal data appears as `[CARD]`, `[EMAIL]`; originals are never stored):
```powershell
python -c "import sqlite3; [print(r) for r in sqlite3.connect('tickets.db').execute('select ticket_id, department, action, reasons, sanitized_message from tickets')]"
```

## Run the tests

```bash
pytest -q                              # 103 passed, 1 skipped (no key, no network, no cost)
pytest -v                              # one line per test
pytest tests/test_api.py -v            # the 26 API tests
pytest tests/test_slide_claims.py -v   # the slide-deck corrections, verified against the SDK
ruff format --check . && ruff check .  # code style
```

The tests drive the **real** TypeSafe SDK through a mocked network (`httpx2.MockTransport`), so the
SDK's request building, parsing, retries and exceptions run for real. They also run from an empty
folder, so your personal `.env` and key are never used.

**The live test** sends one real ticket to Jev (needs your key):
```powershell
$env:RUN_LIVE_TESTS = "1"; pytest -m live -s     # PowerShell
Remove-Item Env:RUN_LIVE_TESTS                   # switch it off again afterwards
```
```bash
RUN_LIVE_TESTS=1 pytest -m live -s               # Git Bash / macOS / Linux
```
Expected: `LIVE: jev-1.13.0 -> billing (1.00), high, auto_route, … ms` and `1 passed`.

## Evaluate decision quality

```bash
python -m evaluation.evaluate                   # backend from .env (the real Jev)
python -m evaluation.evaluate --backend mock    # pipeline check only, NOT a Jev measurement
```
It reports department accuracy, per-class precision/recall/F1, a confusion matrix, accuracy by tag
(easy, ambiguous, multi-topic, human, adversarial), priority accuracy, needs-a-person accuracy,
**automation coverage and accuracy on auto-routed tickets** (the number that matters in production),
calibration (ECE, Brier), errors, latency and a **threshold sweep** for choosing
`AUTO_ROUTE_MIN_CONFIDENCE` from data. Each report is saved in `evaluation/results/` with the backend,
model and policy recorded.

**One live run** (`jev-1.13.0`, 40 synthetic tickets): department accuracy 1.00 (including the
ambiguous and adversarial ones), priority 0.75 exact and 1.00 within one level, needs-a-person 0.95,
85% of tickets automated with **100% accuracy on those**, typical latency ≈ 250 ms. A second run gave
identical decisions.

> These tickets and labels were written by the course author and are fairly clear. Treat the numbers
> as a demonstration of the method, not a benchmark. Run the same evaluation on **your own** labelled
> tickets (the review endpoint collects them) before trusting any threshold.

## Docker

Needs [Docker Desktop](https://www.docker.com/products/docker-desktop/) (AMD64 for Intel/AMD processors,
ARM64 for Snapdragon; check with `$env:PROCESSOR_ARCHITECTURE`). Stop any `uvicorn` first, since both use port 8000.

```bash
docker build -t practical-jev-ai .
docker run --rm -p 8000:8000 --env-file .env -e DATABASE_URL=sqlite:////data/tickets.db -v jevdata:/data practical-jev-ai
```

- `--env-file .env` passes your key and settings (the key is not baked into the image).
- `-e DATABASE_URL=…` keeps the database in `/data` inside the container. **Required**: your `.env` value is a local path that the container's non-root user can't write to.
- `-v jevdata:/data` stores it in a volume, so tickets survive restarts. Test it: create a ticket, press Ctrl + C, run again, and `GET /tickets/{id}` still finds it.

## Configuration

All settings are environment variables (see `.env.example`). Empty values in `.env` fall back to the defaults.

| Variable | Default | Meaning |
|---|---|---|
| `JEV_BACKEND` | `typesafe` | `typesafe` (real API) or `mock` (offline, not Jev) |
| `TYPESAFE_API_KEY` | — | your key |
| `JEV_MODEL` | `jev-latest` | **pin a version (e.g. `jev-1.13.0`)** for consistent results and before tuning thresholds; aliases move |
| `JEV_TIMEOUT_SECONDS` / `JEV_MAX_RETRIES` / `JEV_RETRY_BUDGET_SECONDS` | 5 / 2 / 10 | per-attempt timeout, SDK retries, total budget |
| `AUTO_ROUTE_MIN_CONFIDENCE` | 0.60 | department confidence needed to auto-route |
| `MIN_TOP2_MARGIN` | 0.15 | minimum gap between the two most likely departments |
| `PRIORITY_MIN_CONFIDENCE` | 0.40 | below this the urgency (SLA) can't be set reliably |
| `HUMAN_REVIEW_NOUL_THRESHOLD` | 0.50 | a person steps in when **any** of the four checks reaches this |
| `CRITICAL_ESCALATION_PROBABILITY` | 0.25 | escalate at this chance of critical, even if it isn't the top level |
| `MANDATORY_REVIEW_PRIORITIES` | `["critical"]` | always reviewed, whatever the confidence (`critical` or `critical,high` also work) |
| `MAX_MESSAGE_CHARS` · `REDACT_PII` · `DATABASE_URL` · `LOG_LEVEL` | 4000 · true · `sqlite:///./tickets.db` · INFO | limits, privacy, infrastructure |

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Activate.ps1 cannot be loaded` / running scripts is disabled | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again |
| `ModuleNotFoundError: No module named 'pydantic'` (or any package) | the project isn't installed in the active `.venv`: run `pip install -e ".[dev,ui]"`. Don't install packages one by one |
| `neither 'setup.py' nor 'pyproject.toml' found` | you're not in the project root; `cd` into the folder that has `pyproject.toml` |
| `Cannot find path ...\system32\.env.example` | the terminal is in the wrong folder; use VS Code's terminal or `cd` to the project |
| `Client setup failed: No API key was provided` | add `TYPESAFE_API_KEY=…` to `.env`, or use `--offline` |
| reason `jev_auth_failed` / `401` | key rejected: create a new one in the console |
| reason `jev_rate_limited`, `jev_timeout` or `jev_unavailable` | network, proxy or a TypeSafe hiccup; tickets still go to a person |
| reason `decision_validation_failed` | an answer failed our checks; look up `jev_request_id` in the logs |
| `PermissionError: Access is denied ... pytest-of-<you>` | folders created by an **Administrator** terminal. Delete them from an admin PowerShell, or run `pytest -q --basetemp="$HOME\pytest-tmp" -p no:cacheprovider`. Use only VS Code's terminal afterwards |
| `93 passed, 2 skipped` instead of `103 passed, 1 skipped` | Streamlit isn't installed (or the wrong `.venv` is active): `pip install -e ".[dev,ui]"` |
| `104 passed` | `RUN_LIVE_TESTS` is still on in this terminal: `Remove-Item Env:RUN_LIVE_TESTS` |
| `docker is not recognized` | install / start Docker Desktop, then fully restart VS Code |
| Docker: `unable to open database file` | add `-e DATABASE_URL=sqlite:////data/tickets.db` to `docker run` |
| port 8000 already in use | another server (uvicorn or a container) is running; stop it with Ctrl + C |
| `Unexpected token` in PowerShell | you pasted output or a prompt (`(.venv) PS C:\...>`) as a command; paste only commands |
| Swagger shows only "default" and Schemas | click **default** to expand the endpoints |
| offline results look wrong | expected: the mock is a keyword heuristic, not Jev |

More, with every command in order: **[docs/command-reference.pdf](docs/command-reference.pdf)**.

## Production considerations

This is a **tutorial-quality reference implementation, not a production-certified system**.
[docs/production-checklist.md](docs/production-checklist.md) lists what's implemented and what to add
before real customer traffic: authentication, Postgres + migrations, a dedicated PII service, an outbox
for downstream actions, alerting, and thresholds tuned on your own labelled data.

## Course materials

| Document | For |
|---|---|
| [modules/](modules/README.md) | the course, one folder per module, in order |
| [Module 1 materials](modules/01-introduction-and-resources/README.md#course-materials-in-this-folder) | `jev-slides.pdf`, the resources PDF, and the verified reading list |
| [docs/command-reference.pdf](docs/command-reference.pdf) | every command, in order, with expected results and fixes |
| [docs/course-outline.md](docs/course-outline.md) | lesson order, timings, objectives, files, slides |
| [docs/instructor-guide.md](docs/instructor-guide.md) | recording script, module by module (incl. a 60-minute version) |
| [docs/slide-companion.md](docs/slide-companion.md) | how to use `jev-slides.pdf`: slide → module, and the verbal corrections |
| [docs/student-guide.md](docs/student-guide.md) | self-paced labs, three exercises, final challenge |
| [docs/architecture.md](docs/architecture.md) | design and data flow |
| [docs/n8n-integration.md](docs/n8n-integration.md) | calling this service from n8n |
| [modules/01-introduction-and-resources/learning-resources.md](modules/01-introduction-and-resources/learning-resources.md) | all 48 resource links, verified and mapped to modules |
| [docs/production-checklist.md](docs/production-checklist.md) | what's done and what isn't |

## Official resources

| Get started | Concepts | Python SDK | Production |
|---|---|---|---|
| [Website](https://typesafe.ai/) | [System One](https://docs.typesafe.ai/concepts/system-one) | [Install](https://docs.typesafe.ai/sdk/python) | [Known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) |
| [Docs](https://docs.typesafe.ai/) | [Primitives](https://docs.typesafe.ai/primitives) | [Usage](https://docs.typesafe.ai/sdk/python/usage) | [Retries](https://docs.typesafe.ai/sdk/python/api/retries) |
| [Console & keys](https://console.typesafe.ai/) | [Confidence](https://docs.typesafe.ai/confidence) | [Responses](https://docs.typesafe.ai/sdk/python/api/types/responses) | [Confidence-gated routing](https://docs.typesafe.ai/patterns/confidence-routing) |
| [Quick start](https://docs.typesafe.ai/introduction/quickstart) | [State](https://docs.typesafe.ai/concepts/state) | [Exceptions](https://docs.typesafe.ai/sdk/python/api/exceptions) | [Models & limits](https://docs.typesafe.ai/models) |
| [API reference](https://docs.typesafe.ai/api) | [How to build](https://docs.typesafe.ai/concepts/how-to-build-with-system-one) | [SDK source](https://github.com/typesafe-ai/typesafe-sdk-python) | [Changelog](https://docs.typesafe.ai/sdk/python/changelog) |

The full list (48 links, including cookbooks and third-party tutorials) is in
[learning-resources.md](modules/01-introduction-and-resources/learning-resources.md).

Tested with `typesafe-sdk` 0.7.4, Python 3.12/3.13, and the live model `jev-1.13.0`.
