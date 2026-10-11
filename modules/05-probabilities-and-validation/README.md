# Module 5 — Probabilities & Validation

⏱ 30:00–40:00 · ⬅ [Module 4](../04-classification-with-jev/README.md) · Next ➡ [Module 6](../06-decision-policy-and-routing/README.md)

**Goal:** turn native Jev answers into your own typed decisions — and reject anything you can't trust.

**Slides:** pages 22, 23 of [jev-slides.pdf](../01-introduction-and-resources/materials/jev-slides.pdf). ⚠️ Both show confidence 0.72 for
probabilities 0.72 / 0.21 / 0.07. The real formula gives **0.58**. Slide 23's `reason_code` and
`risk_level` fields don't exist.

## Concepts

- **Two schemas.** The SDK's native answers vs. *your* application decision. The parser is the only
  bridge, so an API change breaks in exactly one place.
- **Confidence formula** (Choice, *n* options): `(p_max − 1/n) / (1 − 1/n)` → (0.72 − 1/3) / (2/3) = 0.58.
- **Type-checked ≠ range-checked.** Verified on SDK 0.7.4: the SDK accepts a confidence of `NaN`,
  `inf` or `1.5`. Your code must check.
- **Most likely level, not `round(score)`.** 51% low / 49% critical has expected score ≈ 1.5 →
  "high", a level the model gave 0%. Use the argmax; keep the score for audit.

## Build

| File | What it does |
|---|---|
| [`app/models/decision.py`](../../app/models/decision.py) | `Department`, `Priority` enums; `TicketDecision` |
| [`app/services/decision_parser.py`](../../app/services/decision_parser.py) | rejects unknown labels, mismatched keys, distributions not summing to ~1, a choice that isn't the argmax, non-finite or out-of-range numbers |

## Run

```bash
python examples/02_typed_decisions.py    # bottom half: REJECTED tampered response -> unexpected department 'legal'
python examples/03_probabilities.py      # bars, reported vs. recomputed confidence, margins, 3 policies
```

## Reading

[Confidence](https://docs.typesafe.ai/confidence) (the key page) ·
[Responses](https://docs.typesafe.ai/sdk/python/api/types/responses)

## ✅ Checkpoint

You can say what confidence 0 and 1 mean, why 0.72 → 0.58, and name five things the parser rejects.

Next ➡ [Module 6 — Decision Policy & Routing](../06-decision-policy-and-routing/README.md)
