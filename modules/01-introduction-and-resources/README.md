# Module 1 — Introduction, Course Materials & Resources

⏱ 00:00–05:00 · ⬅ [Course home](../../README.md) · Next ➡ [Module 2](../02-jev-fundamentals/README.md)

**Goal:** know what you'll build, how the course is organized, and where every material and
reference lives before writing any code.

## The problem we solve

A support team receives billing, technical, account, sales and general messages. We don't need an
AI to *write* replies. We need fast, reliable **decisions**: which team, how urgent, does a human
need to look, and a system that knows **when it isn't sure**.

By the end you'll have a FastAPI service that makes those decisions with **Jev** (TypeSafe AI's
System One model) and applies Python business rules to route each ticket automatically or hold it
for a human.

## The ideas behind Jev

**Why "System One"?** The name comes from Daniel Kahneman's *Thinking, Fast and Slow*. Our minds
have two modes: **System 1** is fast and intuitive (you know 2 + 2 instantly), and **System 2** is
slow and deliberate (you have to work out 17 × 24). System 1 is powerful but biased: it anchors on
the first number it sees, feels confident without enough information, and judges a whole
experience by how it ended. Jev is a fast, System 1-style model, but its answers are **typed,
probabilistic and testable**. In this course, our Python code and human review play **System 2**:
they check the facts, apply the rules, and step in when Jev isn't sure.

**Why "Jev"?** After the economist **William Stanley Jevons**. The *Jevons paradox* says that when
something becomes cheaper and more efficient, people end up using **more** of it, not less.
TypeSafe's bet is that fast, cheap AI decisions will appear everywhere inside software.

## Course map

| # | Module | Time | You leave with |
|---|---|---|---|
| **1** | **Introduction, materials & resources** *(you are here)* | 00–05 | the map, the slides, the reading list |
| 2 | [Jev fundamentals](../02-jev-fundamentals/README.md) | 05–12 | state, questions, Choice / Score / Noul, confidence |
| 3 | [Setup & first request](../03-setup-and-first-request/README.md) | 12–20 | a working environment and one real API call |
| 4 | [Classification with Jev](../04-classification-with-jev/README.md) | 20–30 | the ticket questions (three decisions) and a Jev client |
| 5 | [Probabilities & validation](../05-probabilities-and-validation/README.md) | 30–40 | typed, validated decisions |
| 6 | [Decision policy & routing](../06-decision-policy-and-routing/README.md) | 40–50 | an automated workflow with human review |
| 7 | [FastAPI & persistence](../07-fastapi-and-persistence/README.md) | 50–60 | a REST API with an audit trail |
| 8 | [Testing & evaluation](../08-testing-and-evaluation/README.md) | 60–68 | a tested pipeline and measured quality |
| 9 | [Production & next steps](../09-production-and-next-steps/README.md) | 68–75 | hardening, business scenarios, exercises |

Each module folder has a README like this one: goal, slide pages, reading, the files to open, the
commands to run, and a ✅ checkpoint. The application code itself lives in one place (`app/`,
`examples/`, `tests/`, `evaluation/`) because it is one program that grows module by module.

## Course materials (in this folder)

| File | What it is |
|---|---|
| [materials/jev-slides.pdf](materials/jev-slides.pdf) | the 31-page deck: opening & intro (pages 1–14), then the Jev slides (pages 15–31) |
| [materials/Jev_Complete_Learning_Resources.pdf](materials/Jev_Complete_Learning_Resources.pdf) | 48 clickable resource links |
| [learning-resources.md](learning-resources.md) | the same 48 links, **checked** against TypeSafe's official index and mapped to modules |

### Where each slide is used

| Slides (PDF pages) | Module |
|---|---|
| 1–3 | 1: opening: title, TypeSafe AI, the founders |
| 4–12 | 1: Daniel Kahneman, *Thinking, Fast and Slow*, and how System 1 / System 2 map to Jev |
| 13–14 | 1: why it's called Jev (William Stanley Jevons) |
| 15, 18–20 | 1: what Jev is; Jev vs. n8n |
| 16, 17, 21 | 2: how it works; vs. LLMs; System One |
| 24 | 3: Jev in Python |
| 25, 26 | 4: support router; email priority |
| 22, 23 | 5: probabilistic outputs; type-safe decisions |
| 31 (steps 4–5) | 6: business rules and actions |
| 30 | 7: connecting your systems |
| 31 (step 6) | 8: measuring results |
| 27–29 | 9: business scenarios |

### Read this before using the slides

The slides are a visual introduction and simplify a few API details. Five things differ in code,
and each correction is verified by `tests/test_slide_claims.py`:

1. The answer field is **`choice`** (filed under *your* question name), not `"decision"` (slides 16, 17, 19, 23).
2. **Confidence is not the top probability**: 0.72 / 0.21 / 0.07 gives confidence **0.58** (slides 22, 23).
3. Jev returns **only the questions you ask**; there's no `reason_code` or `risk_level` (slide 23).
4. A request is `{state, model, questions}`, not `{question, choices, input}` (slide 30).
5. **Jev predicts; your code routes and acts** (slides 25, 28, 31).

Percentages on the slides are illustrative, not Jev outputs or measured results.
Full slide-by-slide notes: [docs/slide-companion.md](../../docs/slide-companion.md).

### Reading for this module

- [TypeSafe AI website](https://typesafe.ai/) and the [launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev): what Jev is
- [API console](https://console.typesafe.ai/): create your API key now (you'll use it in Module 3)
- The official domain is **typesafe.ai**. The independent guides in the PDF are on **typesafeai.org**,
  a different site; prefer the official docs when they disagree, and never paste a key into a third-party site.

## Two ways to follow along

| | You need | Answers come from |
|---|---|---|
| **Live** (recommended) | a TypeSafe API key | the real Jev model |
| **Offline** | nothing | a keyword mock, clearly labelled. It runs the real SDK but its answers are **not** Jev |

Every example accepts `--offline`; the API server uses `JEV_BACKEND=mock`.

## Demo: the finished system

Watch this now; you'll set it up yourself in Module 3.

```bash
uvicorn app.main:app --reload        # then open http://127.0.0.1:8000/docs
```

Send `{"ticket_id": "TICKET-001", "customer_id": "CUSTOMER-100", "message": "I was charged twice for my subscription and need a refund."}`
to `POST /tickets`, then a vague one like `"hello??"`. Compare `department`, `confidence`,
`action`, `queue`, `reasons` and `model` between the two, then open `GET /metrics`.

## Prerequisites

Basic Python, REST and JSON; Python 3.11+ installed; Git. No prior AI experience is needed.

## ✅ Checkpoint

You can say what the service does, name the four decisions it makes (department, priority,
needs-human, and the automation policy), and find the slides and reading list.

Next ➡ [Module 2 — Jev fundamentals](../02-jev-fundamentals/README.md)
