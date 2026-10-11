# Module 6 — Decision Policy & Routing

⏱ 40:00–50:00 · ⬅ [Module 5](../05-probabilities-and-validation/README.md) · Next ➡ [Module 7](../07-fastapi-and-persistence/README.md)

**Goal:** decide *whether to act* on a prediction, with configurable business rules and a human in the loop.

**Slides:** page 17 (steps 4–5) of [jev-slides.pdf](../01-introduction-and-resources/materials/jev-slides.pdf): high confidence → auto, uncertain
→ review, sensitive → mandatory approval. That's exactly this module. Its percentages are illustrative.

## Build

1. **The policy** — [`app/policies/automation_policy.py`](../../app/policies/automation_policy.py).
   Rules are checked independently and **every** fired reason is recorded; any one sends the
   ticket to a human:
   - business rules (critical priority; P(critical) ≥ limit) — **confidence can't override these**;
   - the model's own Noul judgment (needs a human);
   - uncertainty gates (department confidence, top-2 margin, priority confidence).
2. **The router** — [`app/services/routing_service.py`](../../app/services/routing_service.py):
   reviewed tickets never reach a department queue; critical goes to escalation; an unknown
   department falls back to the general queue.
3. **The pipeline** — [`app/services/decision_service.py`](../../app/services/decision_service.py):
   any Jev failure becomes `inference_failed` + human review. The ticket is never lost.

## Run

```bash
python examples/04_automated_routing.py             # live batch
python examples/04_automated_routing.py --offline   # includes a simulated timeout (T-7)
```

## Key idea

`AUTO_ROUTE_MIN_CONFIDENCE=0.60` is **our** policy choice, not a TypeSafe recommendation. You'll
choose it from data in Module 8. "Confident and wrong" still happens: the policy reduces risk,
it doesn't remove it.

## Reading

[Confidence-gated routing](https://docs.typesafe.ai/patterns/confidence-routing) ·
[Intent routing](https://docs.typesafe.ai/patterns/intent-routing) ·
[How to build with TypeSafe](https://docs.typesafe.ai/concepts/how-to-build-with-system-one)

## ✅ Checkpoint

You can explain why a critical ticket is reviewed even at confidence 1.0, and what happens when Jev is down.

Next ➡ [Module 7 — FastAPI & Persistence](../07-fastapi-and-persistence/README.md)
