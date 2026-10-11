# Course Outline

**Practical Jev AI Engineering — Build Production-Ready Decision Systems with Python**
*From Typed Probabilistic Decisions to Real-World AI Automation*

- **Duration:** ~75 minutes of video (+ optional exercises)
- **Audience:** Python, backend and AI engineers integrating AI decisions into applications
- **Prerequisites:** basic Python, REST, JSON, and a general idea of what an AI model is
- **Outcome:** a tested FastAPI service that classifies, prioritizes and routes support tickets
  with Jev, with a configurable confidence policy, human review, audit trail, and evaluation

Each module has its own folder under [`modules/`](../modules/README.md) with a README: goal, slide
pages, reading, files, commands and a checkpoint. Slide numbers are page numbers in
[`jev-slides.pdf`](../modules/01-introduction-and-resources/materials/jev-slides.pdf); see
[slide-companion.md](slide-companion.md) for the corrections to make while showing them.

| # | Time | Module | Learning objectives | Code & materials | Slides |
|---|---|---|---|---|---|
| 1 | 00:00–05:00 | [Introduction, materials & resources](../modules/01-introduction-and-resources/README.md) | See the finished system; understand the problem (routing tickets reliably, not writing replies); know the course map, the slides and the reading list | slides PDF, resources PDF, `learning-resources.md`; `app/main.py` (run only), Swagger UI | 1, 4–6 |
| 2 | 05:00–12:00 | [Jev fundamentals](../modules/02-jev-fundamentals/README.md) | System One vs. LLM; state + questions; Choice / Score / Noul; probabilities vs. confidence; what Jev is bad at | `app/services/questions.py` (read only) | 2, 3, 7 |
| 3 | 12:00–20:00 | [Setup & first request](../modules/03-setup-and-first-request/README.md) | venv, install SDK, configure key safely; first authenticated call; inspect raw response; auth & network errors | `.env.example`, `examples/_common.py`, `examples/01_first_request.py` | 10 |
| 4 | 20:00–30:00 | [Classification with Jev](../modules/04-classification-with-jev/README.md) | Design the three ticket questions; write literal criteria; one call, parallel questions; wrap the SDK and map its exceptions | `app/services/questions.py`, `app/services/jev_client.py`, `examples/02_typed_decisions.py` | 11, 12 |
| 5 | 30:00–40:00 | [Probabilities & validation](../modules/05-probabilities-and-validation/README.md) | Native vs. app schema; enums + Pydantic; reject unknown labels and broken distributions; argmax vs. expected score; confidence formula; margins | `app/models/decision.py`, `app/services/decision_parser.py`, `examples/03_probabilities.py` | 8, 9 |
| 6 | 40:00–50:00 | [Decision policy & routing](../modules/06-decision-policy-and-routing/README.md) | Thresholds as business policy; mandatory rules beat confidence; abstention; conflicting/ambiguous predictions; graceful degradation | `app/policies/automation_policy.py`, `app/services/routing_service.py`, `app/services/decision_service.py`, `examples/04_automated_routing.py` | 17 (steps 4–5) |
| 7 | 50:00–60:00 | [FastAPI & persistence](../modules/07-fastapi-and-persistence/README.md) | Routes, response models, status codes, DI, idempotency, SQLite audit record, review endpoint, central error handling | `app/api/routes.py`, `app/main.py`, `app/database/*`, `app/models/ticket.py` | 16 |
| 8 | 60:00–68:00 | [Testing & evaluation](../modules/08-testing-and-evaluation/README.md) | Mock the network, not your code; failure-mode tests; labelled data; accuracy on auto-routed tickets; calibration; threshold sweep | `tests/*`, `evaluation/*` | 17 (step 6) |
| 9 | 68:00–75:00 | [Production & next steps](../modules/09-production-and-next-steps/README.md) | Secrets, retries/timeouts, structured logs, PII, health/metrics, Docker, what's still missing; the deck's business scenarios built correctly (numbers and times computed in code); exercises | `app/utils/*`, `Dockerfile`, `examples/05_business_patterns.py`, `docs/production-checklist.md` | 13–15 |

## Concepts introduced exactly once

| Concept | Introduced in | Re-used in |
|---|---|---|
| state / questions / primitives | 2 | 3–6 |
| SDK exception hierarchy | 3 (catch) → 4 (map to app errors) | 6, 8 |
| native vs. application schema | 5 | 7 |
| confidence formula, margin, Noul `|2p-1|` | 5 | 6, 8 |
| thresholds are policy | 6 | 8 (sweep), 9 |
| compute numbers and dates in code, give Jev facts | 2 (limits) | 9 (`examples/05`) |
| idempotency | 7 | 9 |
| mock the network | 8 | — |

## Exercises (after the video)

1. **Add the `shipping` category** from slides 11 and 14: enum, criteria, queue, tests, dataset rows.
2. **Change the confidence policy** and compare coverage vs. accuracy with the evaluation sweep.
3. **Add a decision question** (e.g. `sentiment` Score or `churn_risk` Noul) and expose it via the API.

**Final challenge:** reuse the architecture for another domain — document classification, GitHub
issue triage, or content moderation. Details in `docs/student-guide.md`.
