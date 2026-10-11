# Slide Deck Companion (`jev.pptx`, 17 slides)

The deck is a strong visual introduction. A few slides simplify the API in ways that would
mislead someone writing code, so this page gives, for every slide: the course module it supports,
the code it connects to, and what to **say on camera** where the slide needs a correction.

Every correction below is checked by `tests/test_slide_claims.py` (run: `pytest tests/test_slide_claims.py -v`).

## Quick reference: the five things to correct verbally

| # | Slides | The slide shows | What the real API does | Verified by |
|---|---|---|---|---|
| 1 | 2, 3, 5, 9 | `"decision": "fraud"` | the field is **`choice`** (Choice answers); answers come back under the **question name you chose**, inside `answers` | `test_real_request_body_shape_differs_from_slide16` |
| 2 | 8, 9 | confidence **0.72** = top probability | confidence is **(p_max − 1/n)/(1 − 1/n)** → 0.72 / 0.21 / 0.07 gives **0.58** | `test_slides_8_and_9_confidence_is_not_the_top_probability` |
| 3 | 9 | `reason_code`, `risk_level` in the output | Jev returns **only the questions you ask**. A risk level is a separate Score question; a "high amount" reason is arithmetic → compute it in code | `test_answers_contain_only_what_was_asked` |
| 4 | 16 | request `{question, choices, input}` | request is `{state, model, questions: {name: {type, instructions, criteria}}}` | `test_real_request_body_shape_differs_from_slide16` |
| 5 | 11, 14, 17 | "Jev routes the request" / Jev → create ticket | Jev **predicts**; **your code** routes and acts. That separation is the whole course | course modules 5–6 |

Also say once, early: **percentages on the slides are illustrative**, not Jev outputs or benchmark
results. That includes slide 17's "87% accuracy / 60% faster / 40% less manual work".

Correct versions of the two JSON snippets, for an overlay or a code cut-in:

```json
// Request (replaces slide 16's snippet)
{
  "state": "I have a billing issue with my order.",
  "model": "jev-latest",
  "questions": {
    "category": {
      "type": "choice",
      "instructions": "Which category does this message belong to?",
      "criteria": {"billing": null, "shipping": null, "technical": null}
    }
  }
}
```
```json
// Response shape (replaces slides 2/3/5/9). Numbers are illustrative.
{
  "model": "jev-1.13.0",
  "answers": {
    "category": {
      "type": "choice",
      "choice": "billing",
      "probabilities": {"billing": 0.92, "shipping": 0.06, "technical": 0.02},
      "confidence": 0.88
    }
  },
  "usage": {"input_tokens": 120, "output_tokens": 10}
}
```

## Slide by slide

### 1. What is Jev? → Module 1
Accurate summary: non-generative, probabilistic, typed, no text generation.
**Add:** the input is **state + typed questions** — not just "data". The questions are what make
the output typed.

### 2. How does Jev work? → Module 1
Fraud example with transaction fields. **Correct #1** (`decision` → `choice`).
**Add:** "pattern analysis / learned signals" are illustrative labels, not documented internals —
TypeSafe hasn't published Jev's architecture. The input fields (`amount: $1,250`) are numeric:
Jev is weak at numbers, so you'd pass *derived facts* (e.g. `amount_above_customer_p95: true`).

### 3. Jev vs. LLMs → Module 1
Good contrast. **Correct #1.** **Add:** they're complementary, not rivals — TypeSafe's own
[intent routing](https://docs.typesafe.ai/patterns/intent-routing) and
[LLM guardrails](https://docs.typesafe.ai/cookbooks/llm_guardrails) patterns use Jev to decide and
an LLM to write. "Not type-safe" for LLMs is about free text; LLM structured-output modes exist
but still need parsing/validation, which is the point being made.

### 4–6. Jev vs. n8n → Module 0 or 8 (positioning)
Fair framing: Jev is a decision component, n8n is an automation platform. Two clarifications:
- Slide 6 "Can use LLMs? No" means *Jev isn't an LLM and doesn't call one*. Jev can still sit
  **next to** LLMs in a system (see above).
- Slide 6 "Can automate tasks? No" is right for Jev alone — that's why this repo wraps Jev in a
  service with a policy. **They combine well:** n8n can call this project's `POST /tickets` and
  branch on `action`. See [n8n-integration.md](n8n-integration.md).

### 7. What is System One AI? → Module 1
Matches TypeSafe's framing (named after Kahneman's *Thinking, Fast and Slow*).
**Add the practical rule:** one atomic, gut-check question per decision; decompose anything
needing multi-step reasoning and combine the parts in code
([how to build](https://docs.typesafe.ai/concepts/how-to-build-with-system-one)).

### 8. Probabilistic outputs → Module 4 ⚠️
**Correct #2** — the most important correction in the deck. Show `examples/03_probabilities.py`,
which prints the API's confidence next to the formula re-computed in Python.
**Add:** confidence is not "the chance the answer is right", and it's never a guarantee.

### 9. Type-safe decisions → Module 4 ⚠️
**Correct #1, #2, #3.** Good moment to show `app/services/decision_parser.py`: "type-safe" means
the answer is always one of your options — your code should still validate ranges (we verified the
SDK will accept a confidence of `NaN` or `1.5`).

### 10. Jev in Python → Module 2 ✅
The code is correct SDK usage — `test_slide10_python_snippet_runs_against_the_real_sdk` runs it.
The deck labels the output "illustrative" — keep that.

### 11. Smart support router → Modules 3 and 5
**Correct #5.** Our project's departments are billing / technical / account / sales / general — no
"shipping". Adding it is **Exercise 1** in the student guide, using this slide as the brief.

### 12. Email prioritization → Module 3
Priority has ordered levels, so the right primitive is **Score**, not Choice — exactly how
`app/services/questions.py` asks for ticket priority. Built correctly in `examples/05_business_patterns.py`.

### 13. Suspicious logins → Module 8
**Add (jaggedness):** "unusual time 2:37 AM" and "unfamiliar location" are comparisons → compute
them in code (`login_hour_is_unusual: true`) and give Jev the facts. The action ("send verification
code") is a policy decision with a deliberately *low* threshold, because a step-up check is cheap.
Built in `examples/05_business_patterns.py`.

### 14–15. Practical business applications → Module 8
Good map of decision → action. Map each to a primitive:
complaints urgent? → **Noul**; invoice needs review? → **Noul** + amount rule in code;
sentiment → **Choice**; lead interest high/medium/low → **Score**. **Correct #5** for the
"workflow action" column.

### 16. How a business owner can get started (1–3) → Module 0/8 ⚠️
Steps are sound. **Correct #4** (request shape). "Connect the data source" maps to `POST /tickets`.

### 17. How a business owner can get started (4–6) → Modules 5 and 7
This slide *is* the course architecture: business rules → automate approved action → measure.
Map it: step 4 = `app/policies/automation_policy.py` (high confidence → auto; uncertain → review;
sensitive → mandatory review), step 5 = `app/services/routing_service.py`, step 6 =
`evaluation/evaluate.py` + `GET /metrics`.
**Say clearly:** the 87% / 60% / 40% figures are illustrative targets, not measured results.
This repo measures accuracy and automation coverage; it does **not** measure response-time or
manual-work savings (see production checklist).

## Offline mode and these slides

`examples/05_business_patterns.py --offline` runs, but the mock is a keyword heuristic: for
example it lets the suspicious login through. That's expected — it shows the plumbing, not Jev.
Record these scenarios against the real API.
