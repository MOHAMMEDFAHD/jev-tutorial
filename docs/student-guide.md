# Student Lab Guide

Work through this at your own pace. Each lab ends with a ✅ check you can verify yourself.
No API key? Add `--offline` to examples and set `JEV_BACKEND=mock` in `.env` — but remember the
mock is a keyword heuristic, **not Jev**, so its numbers say nothing about model quality.

## Lab 0 — Setup (10 min)

```bash
python3 -m venv .venv && source .venv/bin/activate      # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env                                    # Windows: Copy-Item .env.example .env
```
Put your key in `.env` (`TYPESAFE_API_KEY=...`).
✅ `pytest -q` ends with `98 passed, 1 skipped`.

## Lab 1 — First request

Run `python examples/01_first_request.py`. Find `model`, `choice`, `probabilities`, `confidence`, `noul`.
Change the message to something about a login problem and re-run.
✅ You can explain why `noul` has no `confidence` field.

## Lab 2 — Typed decisions

Run `python examples/02_typed_decisions.py`. Read `app/services/decision_parser.py`.
✅ You can list five things the parser rejects.

## Lab 3 — Probabilities

Run `python examples/03_probabilities.py`. Compute by hand the confidence for probabilities
`(0.6, 0.3, 0.1)`: `(0.6 − 1/3) / (1 − 1/3) = 0.4`.
✅ You can explain why a ticket with confidence 0.95 can still be wrong.

## Lab 4 — Policy & routing

Run `python examples/04_automated_routing.py`. For every held ticket, find the rule that fired in
`app/policies/automation_policy.py`.
✅ You can explain why a critical ticket is reviewed even at confidence 1.0.

## Lab 5 — The API

```bash
uvicorn app.main:app --reload
```
In `http://127.0.0.1:8000/docs`: create a ticket; send the same request again (200 + `Idempotent-Replay`);
change the message, same id (409); review a held ticket; check `/metrics`.
✅ You can explain why retries can't route a ticket twice.

## Lab 6 — Tests & evaluation

```bash
pytest -q
python -m evaluation.evaluate
```
✅ From the threshold sweep, you can name the threshold you would ship and say what it costs in coverage.

## Lab 7 — Business scenarios from the slides

Run `python examples/05_business_patterns.py`. It rebuilds the deck's email, login, invoice and
feedback scenarios with the real API. For each one, find which parts are computed **in Python**
(login hour, known country, invoice limit) and which are asked of **Jev**.
✅ You can explain why "is 2:37 AM unusual?" is answered in code, not by the model.

## Reading

Each lab's background reading is mapped in [learning-resources.md](../modules/01-introduction-and-resources/learning-resources.md).
Start with **Confidence** and **Known limitations**. The guides on `typesafeai.org` are third-party,
not TypeSafe's (`typesafe.ai`); prefer the official docs when they disagree.

---

## Exercise 1 — Add the `shipping` category (slides 25 and 28)

The deck's support router sends "My order hasn't arrived yet" to a **shipping** team. Our engine
doesn't have one yet: today that message lands in `general` or gets held for review. Add it.

1. `app/models/decision.py`: add `SHIPPING = "shipping"` to `Department`.
2. `app/services/questions.py`: add a literal criterion, e.g. *"Order delivery, tracking,
   delayed or missing packages, wrong or damaged items received."* Then check the boundaries:
   a **refund for a damaged item** — billing or shipping? Decide, and write the rule into the
   criteria (Jev reads instructions literally).
3. `app/services/routing_service.py`: add `Department.SHIPPING: "shipping_queue"`.
4. Run `pytest` **before** step 3, then after it. Before: exactly one failure,
   `test_every_department_has_its_own_queue`. That guard exists because a department with no
   queue would otherwise fall back to `general_queue` silently. After step 3: all green. The other
   tests read the departments from the `Department` enum, so they need no edits. Optionally add
   `(Department.SHIPPING, "shipping_queue")` to the parametrized list in `tests/test_routing.py`.
5. Add 4–5 labelled shipping tickets to `evaluation/sample_tickets.json` (include one ambiguous
   "damaged item, want my money back") and re-run the evaluation.

✅ `pytest` passes; with a real key, "My order hasn't arrived yet" lands in `shipping_queue` or is held
with a reason. (With `--offline` it is held: the keyword mock knows nothing about shipping. That's expected.)

## Exercise 2 — Change the confidence policy and observe the effect

1. Run `python -m evaluation.evaluate` and save the sweep.
2. Set `AUTO_ROUTE_MIN_CONFIDENCE=0.8` in `.env`; run again. Then `0.4`.
3. Fill in:

| threshold | coverage | accuracy on auto-routed | wrong auto-routes |
|---|---|---|---|
| 0.4 | | | |
| 0.6 | | | |
| 0.8 | | | |

4. Try `MIN_TOP2_MARGIN=0` and see whether the margin rule was doing any work.

✅ You can argue for one setting using the table — not intuition.

## Exercise 3 — Add a decision question and expose it via the API

Add **customer sentiment** (Score: `calm`, `frustrated`, `angry`).

1. `questions.py`: add `SENTIMENT_KEY` and a `Score` to `build_ticket_questions()` (still one API call).
2. `models/decision.py`: a `Sentiment` enum and a field on `TicketDecision`.
3. `decision_parser.py`: parse + validate it like `parse_priority`.
4. `database/models.py`: a `sentiment` column. (Delete `tickets.db` — there are no migrations.)
5. `repository.py`, `models/ticket.py` (`TicketResponse.sentiment`), `api/routes.py` (`to_response`).
6. Optional policy rule: angry **and** high priority → human review. Add a test.
7. Tests: run `pytest` after step 3 and read the failures before fixing them (expect ~17, across the
   API and parser tests). API tickets now come back `decision_validation_failed`, because `wire_response()` in `tests/conftest.py` doesn't include a
   `sentiment` answer and the parser refuses an incomplete response. That's the behaviour you want in
   production. Add a `sentiment` Score answer to `wire_response()`, and add `"sentiment": "score"` to
   the expected question types in `test_sends_documented_request_shape`.

✅ `POST /tickets` returns `sentiment`; tests pass.

---

## Final challenge — a decision engine for another domain

Rebuild the same architecture for one of:

- **GitHub issue triage:** labels (bug / feature / question / docs), severity (Score),
  "is this a security report?" (Noul → never auto-label, always to the security team).
- **Document intake:** document type (invoice / contract / receipt / other), "contains personal data?"
  (Noul), routing to processing queues.
- **Content moderation:** violation category (Choice incl. `none`), severity (Score); pass / review /
  block thresholds, with "block" requiring higher confidence than "pass".

Requirements:
1. One Jev request per item, with all questions in it.
2. A parser that rejects anything outside your enums.
3. A policy with at least one rule that confidence cannot override.
4. Graceful degradation when Jev fails.
5. Tests with the network mocked, plus one failure-mode test per Jev error type.
6. A labelled set of ≥ 30 items and an evaluation report with a threshold sweep.
7. A short README explaining which thresholds you chose **and the evidence for them**.
