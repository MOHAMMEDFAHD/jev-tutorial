# Slide Deck Companion (`jev-slides.pdf`, 31 pages)

The deck is in [Module 1](../modules/01-introduction-and-resources/README.md):
[`materials/jev-slides.pdf`](../modules/01-introduction-and-resources/materials/jev-slides.pdf). Page N of the PDF = slide N.

The deck has two parts: an **opening and intro** (pages 1–14: TypeSafe, the founders,
Daniel Kahneman's *Thinking, Fast and Slow*, and Jevons) and the **Jev slides** (pages 15–31).

The deck is a strong visual introduction. A few slides simplify the API in ways that would
mislead someone writing code, so this page gives, for every slide: the course module it supports,
the code it connects to, and what to **say on camera** where the slide needs a correction.

Every correction below is checked by `tests/test_slide_claims.py` (run: `pytest tests/test_slide_claims.py -v`).

## Quick reference: the five things to correct verbally

| # | Slides | The slide shows | What the real API does | Verified by |
|---|---|---|---|---|
| 1 | 16, 17, 19, 23 | `"decision": "fraud"` | the field is **`choice`** (Choice answers); answers come back under the **question name you chose**, inside `answers` | `test_real_request_body_shape_differs_from_slide30` |
| 2 | 22, 23 | confidence **0.72** = top probability | confidence is **(p_max − 1/n)/(1 − 1/n)** → 0.72 / 0.21 / 0.07 gives **0.58** | `test_slides_22_and_23_confidence_is_not_the_top_probability` |
| 3 | 23 | `reason_code`, `risk_level` in the output | Jev returns **only the questions you ask**. A risk level is a separate Score question; a "high amount" reason is arithmetic → compute it in code | `test_answers_contain_only_what_was_asked` |
| 4 | 30 | request `{question, choices, input}` | request is `{state, model, questions: {name: {type, instructions, criteria}}}` | `test_real_request_body_shape_differs_from_slide30` |
| 5 | 25, 28, 31 | "Jev routes the request" / Jev → create ticket | Jev **predicts**; **your code** routes and acts. That separation is the whole course | course modules 6–7 |

Also say once, early: **percentages on the slides are illustrative**, not Jev outputs or benchmark
results. That includes slide 31's "87% accuracy / 60% faster / 40% less manual work".

Correct versions of the two JSON snippets, for an overlay or a code cut-in:

```json
// Request (replaces slide 30's snippet)
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
// Response shape (replaces slides 16/17/19/23). Numbers are illustrative.
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

## Opening & intro (pages 1–14) → Module 1

These slides explain *why* Jev exists before any code. They're accurate as narrated in the
recording scripts; a few points to keep in mind:

| Page | Slide | Note |
|---|---|---|
| 1 | Jev Course | title |
| 2 | TypeSafe AI | the company behind Jev (San Francisco AI lab) |
| 3 | Founders | Diogo Almeida (CEO), Erik Gafni (CTO), Sasha Sheng (COO). "Co-inventor of RLHF" is TypeSafe's own description; on camera, the safer wording is that he **worked on** RLHF, InstructGPT and ChatGPT at OpenAI |
| 4–5 | Daniel Kahneman; *Thinking, Fast and Slow* | Nobel Prize in Economics, 2002. TypeSafe's "System One" name comes from this book. Page 5 has the "2 + 2 / 17 × 24" hook: pause so viewers try it |
| 6 | System 1 × Jev × System 2 | Jev is the **System 1** part; in this course, our Python code and human review play **System 2** |
| 7 | Anchoring & availability | the 40/25/20/15 weights are **combined by your code**, not by Jev |
| 8 | Confidence is not certainty | the 0.80 / 0.50 thresholds are **example policy**, tuned with data (Module 8) |
| 9 | Loss aversion | Jev estimates the risk; **company policy** decides how careful to be |
| 10 | Peak-end rule | Jev judges each interaction; **your code** counts and summarizes (Jev is weak at counting) |
| 11 | Base rates | Jev doesn't know your history: **your code** looks up base rates and passes them as facts |
| 12 | Responsible automation | ⚠️ the gauge shows confidence **0.72**, equal to the top probability. For 0.72 / 0.20 / 0.08 the real confidence is about **0.58**. Narrate "valid refund: 72%", or change the gauge to 0.58 |
| 13–14 | "Jev was named after who?"; William Stanley Jevons | the **Jevons paradox**: when something gets cheaper and more efficient, people use more of it. That's TypeSafe's thesis for cheap, fast AI decisions |

## Jev slides (pages 15–31)

### 15. What is Jev? → Module 1
Accurate summary: non-generative, probabilistic, typed, no text generation.
**Add:** the input is **state + typed questions** — not just "data". The questions are what make
the output typed.

### 16. How does Jev work? → Module 2
Fraud example with transaction fields. **Correct #1** (`decision` → `choice`).
**Add:** "pattern analysis / learned signals" are illustrative labels, not documented internals —
TypeSafe hasn't published Jev's architecture. The input fields (`amount: $1,250`) are numeric:
Jev is weak at numbers, so you'd pass *derived facts* (e.g. `amount_above_customer_p95: true`).

### 17. Jev vs. LLMs → Module 2
Good contrast. **Correct #1.** **Add:** they're complementary, not rivals — TypeSafe's own
[intent routing](https://docs.typesafe.ai/patterns/intent-routing) and
[LLM guardrails](https://docs.typesafe.ai/cookbooks/llm_guardrails) patterns use Jev to decide and
an LLM to write. "Not type-safe" for LLMs is about free text; LLM structured-output modes exist
but still need parsing/validation, which is the point being made.

### 18–20. Jev vs. n8n → Module 1 or 9 (positioning)
Fair framing: Jev is a decision component, n8n is an automation platform. Two clarifications:
- Slide 20 "Can use LLMs? No" means *Jev isn't an LLM and doesn't call one*. Jev can still sit
  **next to** LLMs in a system (see above).
- Slide 20 "Can automate tasks? No" is right for Jev alone — that's why this repo wraps Jev in a
  service with a policy. **They combine well:** n8n can call this project's `POST /tickets` and
  branch on `action`. See [n8n-integration.md](n8n-integration.md).

### 21. What is System One AI? → Module 2
Matches TypeSafe's framing (named after Kahneman's *Thinking, Fast and Slow*).
**Add the practical rule:** one atomic, gut-check question per decision; decompose anything
needing multi-step reasoning and combine the parts in code
([how to build](https://docs.typesafe.ai/concepts/how-to-build-with-system-one)).

### 22. Probabilistic outputs → Module 5 ⚠️
**Correct #2** — the most important correction in the deck. Show `examples/03_probabilities.py`,
which prints the API's confidence next to the formula re-computed in Python.
**Add:** confidence is not "the chance the answer is right", and it's never a guarantee.

### 23. Type-safe decisions → Module 5 ⚠️
**Correct #1, #2, #3.** Good moment to show `app/services/decision_parser.py`: "type-safe" means
the answer is always one of your options — your code should still validate ranges (we verified the
SDK will accept a confidence of `NaN` or `1.5`).

### 24. Jev in Python → Module 3 ✅
The code is correct SDK usage — `test_slide24_python_snippet_runs_against_the_real_sdk` runs it.
The deck labels the output "illustrative" — keep that.

### 25. Smart support router → Modules 4 and 6
**Correct #5.** Our project's departments are billing / technical / account / sales / general — no
"shipping". Adding it is **Exercise 1** in the student guide, using this slide as the brief.

### 26. Email prioritization → Module 4
Priority has ordered levels, so the right primitive is **Score**, not Choice — exactly how
`app/services/questions.py` asks for ticket priority. Built correctly in `examples/05_business_patterns.py`.

### 27. Suspicious logins → Module 9
**Add (jaggedness):** "unusual time 2:37 AM" and "unfamiliar location" are comparisons → compute
them in code (`login_hour_is_unusual: true`) and give Jev the facts. The action ("send verification
code") is a policy decision with a deliberately *low* threshold, because a step-up check is cheap.
Built in `examples/05_business_patterns.py`.

### 28–29. Practical business applications → Module 9
Good map of decision → action. Map each to a primitive:
complaints urgent? → **Noul**; invoice needs review? → **Noul** + amount rule in code;
sentiment → **Choice**; lead interest high/medium/low → **Score**. **Correct #5** for the
"workflow action" column.

### 30. How a business owner can get started (1–3) → Module 1/9 ⚠️
Steps are sound. **Correct #4** (request shape). "Connect the data source" maps to `POST /tickets`.

### 31. How a business owner can get started (4–6) → Modules 6 and 8
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
