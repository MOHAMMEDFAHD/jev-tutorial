# Course Outline

**Practical Jev AI Engineering — Build Production-Ready Decision Systems with Python**
*From Typed Probabilistic Decisions to Real-World AI Automation*

- **Duration:** ~75 minutes of video (+ optional exercises)
- **Audience:** Python, backend and AI engineers integrating AI decisions into applications
- **Prerequisites:** basic Python, REST, JSON, and a general idea of what an AI model is
- **Outcome:** a tested FastAPI service that classifies, prioritizes and routes support tickets
  with Jev, with a configurable confidence policy, human review, audit trail, and evaluation

Slide numbers refer to `jev.pptx`; see [slide-companion.md](slide-companion.md) for the corrections
to make while showing them. Reading for each module is in [learning-resources.md](learning-resources.md).

| # | Time | Module | Learning objectives | Code files | Slides |
|---|---|---|---|---|---|
| 0 | 00:00–05:00 | Introduction & live demo | See the finished system; understand the problem (routing tickets reliably, not writing replies) | `app/main.py` (run only), Swagger UI | 1, 4–6 |
| 1 | 05:00–12:00 | Jev fundamentals | System One vs. LLM; state + questions; Choice / Score / Noul; probabilities vs. confidence; what Jev is bad at | `app/services/questions.py` (read only) | 2, 3, 7 |
| 2 | 12:00–20:00 | Environment & first request | venv, install SDK, configure key safely; first authenticated call; inspect raw response; auth & network errors | `.env.example`, `examples/01_first_request.py` | 10 |
| 3 | 20:00–30:00 | Classification with Jev | Design the three ticket questions; write literal criteria; one call, parallel questions; wrap the SDK and map its exceptions | `app/services/questions.py`, `app/services/jev_client.py`, `examples/02_typed_decisions.py` | 11, 12 |
| 4 | 30:00–40:00 | Probabilities & validation | Native vs. app schema; enums + Pydantic; reject unknown labels and broken distributions; argmax vs. expected score; confidence formula; margins | `app/models/decision.py`, `app/services/decision_parser.py`, `examples/03_probabilities.py` | 8, 9 |
| 5 | 40:00–50:00 | Decision policy & routing | Thresholds as business policy; mandatory rules beat confidence; abstention; conflicting/ambiguous predictions; graceful degradation | `app/policies/automation_policy.py`, `app/services/routing_service.py`, `app/services/decision_service.py`, `examples/04_automated_routing.py` | 17 (steps 4–5) |
| 6 | 50:00–60:00 | FastAPI integration & persistence | Routes, response models, status codes, DI, idempotency, SQLite audit record, review endpoint, central error handling | `app/api/routes.py`, `app/main.py`, `app/database/*`, `app/models/ticket.py` | 16 |
| 7 | 60:00–68:00 | Testing & evaluation | Mock the network, not your code; failure-mode tests; labelled data; accuracy on auto-routed tickets; calibration; threshold sweep | `tests/*`, `evaluation/*` | 17 (step 6) |
| 8 | 68:00–75:00 | Production hardening & recap | Secrets, retries/timeouts, structured logs, PII, health/metrics, Docker, what's still missing; the deck's business scenarios built correctly (numbers and times computed in code); exercises | `app/utils/*`, `Dockerfile`, `examples/05_business_patterns.py`, `docs/production-checklist.md` | 13–15 |

## Concepts introduced exactly once

| Concept | Introduced in | Re-used in |
|---|---|---|
| state / questions / primitives | 1 | 2–5 |
| SDK exception hierarchy | 2 (catch) → 3 (map to app errors) | 5, 7 |
| native vs. application schema | 4 | 6 |
| confidence formula, margin, Noul `|2p-1|` | 4 | 5, 7 |
| thresholds are policy | 5 | 7 (sweep), 8 |
| compute numbers and dates in code, give Jev facts | 1 (limits) | 8 (`examples/05`) |
| idempotency | 6 | 8 |
| mock the network | 7 | — |

## Exercises (after the video)

1. **Add the `shipping` category** from slides 11 and 14: enum, criteria, queue, tests, dataset rows.
2. **Change the confidence policy** and compare coverage vs. accuracy with the evaluation sweep.
3. **Add a decision question** (e.g. `sentiment` Score or `churn_risk` Noul) and expose it via the API.

**Final challenge:** reuse the architecture for another domain — document classification, GitHub
issue triage, or content moderation. Details in `docs/student-guide.md`.
