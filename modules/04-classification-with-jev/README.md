# Module 4 — Classification with Jev

⏱ 20:00–30:00 · ⬅ [Module 3](../03-setup-and-first-request/README.md) · Next ➡ [Module 5](../05-probabilities-and-validation/README.md)

**Goal:** turn the toy request into the real decision problem and wrap the SDK in a client the
rest of the app can depend on.

**Slides:** pages 25, 26 of [jev-slides.pdf](../01-introduction-and-resources/materials/jev-slides.pdf). Slide 25 says Jev "routes" — it only
predicts; our code routes (Module 6). Slide 26's priority has ordered levels, so it's a **Score**.

## Build

1. **The questions** — [`app/services/questions.py`](../../app/services/questions.py):
   department (**Choice**, 5 options), priority (**Score**, 4 ordered levels), needs-human (**Noul**).
   Write criteria literally, including boundary cases ("refunds" under billing, "cancelling" under
   account): Jev answers the question you wrote, not the one you meant.
2. **The client** — [`app/services/jev_client.py`](../../app/services/jev_client.py):
   `evaluate_ticket()` sends **one** request with all three questions, then maps SDK exceptions to
   app errors (`JevAuthError`, `JevRateLimitError`, `JevTimeoutError`, …) so the rest of the app
   never imports SDK error classes. Retries: the SDK already retries 429/5xx/timeouts with backoff,
   so we **configure** `RetryPolicy` instead of writing a loop.

## Run

```bash
python examples/02_typed_decisions.py          # top half: native answers
```
[`examples/02_typed_decisions.py`](../../examples/02_typed_decisions.py) — notice `priority.score`
is a float (probability-weighted) and `legend` maps levels to your text.

## Common mistakes

Overlapping criteria; one question per request (slow, costly); catching bare `Exception`.
Option order can bias jev-1.13 toward the first Choice option — try shuffling and compare.

## Reading

[Choice](https://docs.typesafe.ai/primitives/choice) ·
[Score](https://docs.typesafe.ai/primitives/score) ·
[Speculative fan-out](https://docs.typesafe.ai/patterns/fan-out) ·
[Async client](https://docs.typesafe.ai/sdk/python/api/clients/async) ·
[Retries](https://docs.typesafe.ai/sdk/python/api/retries)

## ✅ Checkpoint

You can explain why all three questions go in one request, and why the app has its own error types.

Next ➡ [Module 5 — Probabilities & Validation](../05-probabilities-and-validation/README.md)
