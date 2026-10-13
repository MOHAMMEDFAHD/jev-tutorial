# Module 2 — Jev Fundamentals

⏱ 05:00–12:00 · ⬅ [Module 1](../01-introduction-and-resources/README.md) · Next ➡ [Module 3](../03-setup-and-first-request/README.md)

**Goal:** understand what Jev is, what it returns, and what it's bad at — before writing code.

**Slides:** pages 16, 17, 21 of [jev-slides.pdf](../01-introduction-and-resources/materials/jev-slides.pdf). On slides 16–17, the output field is
`choice`, not `"decision"`.

## Concepts

1. **Decisions, not text.** An LLM writes text for people; Jev returns typed decisions for code,
   like a function call: state in, typed probabilistic answers out.
2. **A request = state + questions.** *State* is the data to judge (a string, object or array).
   *Questions* is a map of names you choose to typed questions. The names are yours and are **not**
   sent to the model; answers come back under the same names.
3. **Three question types** ([primitives](https://docs.typesafe.ai/primitives)):

   | Type | Ask it… | Answer fields |
   |---|---|---|
   | **Choice** | to pick one option (≤ 255) — *which team?* | `choice`, `probabilities`, `confidence` |
   | **Score** | to rate on ordered levels (2–10) — *how urgent?* | `score`, `probabilities`, `legend`, `confidence` |
   | **Noul** | whether a statement is true — *needs a human?* | `noul` (probability of yes; no `confidence` field) |

4. **One request, many questions.** All questions are evaluated in parallel against the same state.
5. **Confidence comes from the probabilities:** 1 when all probability is on one option, 0 at an
   even split. It is **not** the top probability and never a guarantee (details in Module 5).
6. **Known limits** ([jev-1.13](https://docs.typesafe.ai/model-jaggedness/jev-1.13)): reads
   instructions literally; weak at arithmetic, counting and date comparison; can favour the first
   Choice option; can be steered by adversarial text in the state; generates no text.
   Rule of thumb: **numbers and dates in code, judgment in Jev.**

## Files

| File | What to look at (read only for now) |
|---|---|
| [`app/services/questions.py`](../../app/services/questions.py) | the questions (three decisions) this course asks about every ticket |

## Reading

[System One](https://docs.typesafe.ai/concepts/system-one) ·
[AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer) ·
[State](https://docs.typesafe.ai/concepts/state) ·
[Primitives](https://docs.typesafe.ai/primitives) ·
[Known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13)

## Common mistakes

Treating Jev like a chatbot ("explain why…"); asking it to count or compare dates; cramming
several judgments into one question.

## ✅ Checkpoint

Pick the primitive: *"which team?"* (Choice), *"how urgent?"* (Score), *"is this a legal
threat?"* (Noul) — and say why confidence 0.95 can still be wrong.

Next ➡ [Module 3 — Setup & Your First Request](../03-setup-and-first-request/README.md)
