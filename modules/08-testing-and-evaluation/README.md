# Module 8 — Testing & Evaluation

⏱ 60:00–68:00 · ⬅ [Module 7](../07-fastapi-and-persistence/README.md) · Next ➡ [Module 9](../09-production-and-next-steps/README.md)

**Goal:** prove the pipeline works, including when things fail, and measure decision quality with data.

**Slides:** page 31 (step 6, "measure the results") of [jev-slides.pdf](../01-introduction-and-resources/materials/jev-slides.pdf). Its 87% / 60% / 40%
are illustrative targets — here you measure real numbers.

## Testing

Strategy: **mock the network, not your code.** [`tests/conftest.py`](../../tests/conftest.py) plugs an
`httpx2.MockTransport` into the real SDK client, so serialization, parsing, retries and exception
types run for real.

```bash
pytest -q                                   # 93 passed, 1 skipped
pytest tests/test_slide_claims.py -v        # the slide corrections, verified
RUN_LIVE_TESTS=1 pytest -m live -s          # one contract test against the real API (needs a key)
```

Worth opening: `test_persistent_rate_limit_raises_after_retry_budget` (asserts 3 calls) and
`test_retrying_same_ticket_does_not_call_jev_twice`.

## Evaluation

```bash
python -m evaluation.evaluate                   # live
python -m evaluation.evaluate --backend mock    # pipeline check only — NOT a Jev result
```

Read the report in this order:
1. backend and model id;
2. department accuracy and the confusion matrix;
3. **accuracy on auto-routed tickets vs. coverage** — the production trade-off;
4. the threshold sweep: pick a threshold and justify it;
5. calibration (ECE, Brier) — 40 tickets is far too few for firm conclusions.

| File | |
|---|---|
| [`evaluation/sample_tickets.json`](../../evaluation/sample_tickets.json) | 40 synthetic, labelled tickets (incl. ambiguous and adversarial cases) |
| [`evaluation/metrics.py`](../../evaluation/metrics.py) | every formula, in plain Python |
| [`evaluation/evaluate.py`](../../evaluation/evaluate.py) | runs the pipeline and the sweep |

**Honesty rule:** mock results are meaningless (the mock's keywords and the labels share an author).
Quote only live numbers, as "on this 40-ticket synthetic set, today".

## Reading

[Confidence](https://docs.typesafe.ai/confidence) ·
[Self-consistency: choices](https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook)

## ✅ Checkpoint

You know which metric to watch before raising automation, and can name the threshold you'd ship.

Next ➡ [Module 9 — Production Hardening & Next Steps](../09-production-and-next-steps/README.md)
