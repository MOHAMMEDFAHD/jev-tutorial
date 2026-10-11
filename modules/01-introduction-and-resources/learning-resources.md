# Learning Resources

The 48 links from *Jev — Complete Learning Resources* (the course PDF), organized by when you'll
need them in this course.

**Verification (11 October 2026):** each official link was checked against TypeSafe's published
documentation index, [`docs.typesafe.ai/llms.txt`](https://docs.typesafe.ai/llms.txt).

| Status | Count | Meaning |
|---|---|---|
| ✅ | 41 | listed in the official index, or linked from typesafe.ai |
| ⚠️ | 1 | **not found** in the official index or the cookbooks page — may have moved or been removed |
| 🔸 | 6 | independent third-party content, not reviewed for accuracy |

> **Domain warning.** The official domain is **typesafe.ai**. The independent guides below are on
> **typesafeai.org**, which is a different site, not operated by TypeSafe AI as far as we can tell.
> Never paste an API key into a third-party site, and prefer the official docs when the two disagree.

## 1. Start here (Modules 1–3)

| Resource | Use it for | |
|---|---|---|
| [TypeSafe AI website](https://typesafe.ai/) | what Jev and System One models are | ✅ |
| [Official documentation](https://docs.typesafe.ai/) | everything | ✅ |
| [API console](https://console.typesafe.ai/) | account, **API keys**, Playground | ✅ |
| [Quick start](https://docs.typesafe.ai/introduction/quickstart) | first request (cURL, Python) — Module 3 | ✅ |
| [Models](https://docs.typesafe.ai/models) | `jev-latest` → versioned id, pricing, rate limits, context length | ✅ |
| [HTTP API reference](https://docs.typesafe.ai/api) | exact request/response fields and error codes | ✅ |
| [Documentation index](https://docs.typesafe.ai/llms.txt) | every page in one list | ✅ |

## 2. Core concepts (Modules 2, 4, 5)

| Resource | Course connection | |
|---|---|---|
| [System One models](https://docs.typesafe.ai/concepts/system-one) | Module 2, slide 21 | ✅ |
| [AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer) | why calibrated decisions, not text — slide 17 | ✅ |
| [State](https://docs.typesafe.ai/concepts/state) | `build_state()` in `app/services/questions.py` | ✅ |
| [Primitives](https://docs.typesafe.ai/primitives) | choosing Choice / Score / Noul | ✅ |
| [Choice](https://docs.typesafe.ai/primitives/choice) | department question | ✅ |
| [Score](https://docs.typesafe.ai/primitives/score) | priority question | ✅ |
| [Noul](https://docs.typesafe.ai/primitives/noul) | needs-human question | ✅ |
| [Confidence](https://docs.typesafe.ai/confidence) | **the** page for Module 5; formulas used in `examples/03` and the slide-8 correction | ✅ |

## 3. Python & JavaScript SDKs (Modules 3–4, 8)

| Resource | Course connection | |
|---|---|---|
| [Python SDK](https://docs.typesafe.ai/sdk/python) | installation | ✅ |
| [Python SDK usage](https://docs.typesafe.ai/sdk/python/usage) | `response_model`, retries, logging, env vars | ✅ |
| [Python API reference](https://docs.typesafe.ai/sdk/python/api) | all classes | ✅ |
| [Synchronous client](https://docs.typesafe.ai/sdk/python/api/clients/sync) | `examples/01`–`03`, `05` | ✅ |
| [Asynchronous client](https://docs.typesafe.ai/sdk/python/api/clients/async) | `app/services/jev_client.py`, `examples/04` | ✅ |
| [Responses](https://docs.typesafe.ai/sdk/python/api/types/responses) | `ChoiceAnswer`, `ScoreAnswer`, `NoulAnswer` → `decision_parser.py` | ✅ |
| [Exceptions](https://docs.typesafe.ai/sdk/python/api/exceptions) | error mapping in `jev_client.py` | ✅ |
| [JavaScript SDK](https://docs.typesafe.ai/sdk/javascript) | if your stack is Node/TypeScript (final challenge) | ✅ |

## 4. Building real applications (Modules 6–7)

| Resource | Where this course applies it | |
|---|---|---|
| [How to build with TypeSafe](https://docs.typesafe.ai/concepts/how-to-build-with-system-one) | the "code stays in control" architecture | ✅ |
| [Intent routing](https://docs.typesafe.ai/patterns/intent-routing) | department → queue routing | ✅ |
| [Confidence-gated routing](https://docs.typesafe.ai/patterns/confidence-routing) | `app/policies/automation_policy.py` | ✅ |
| [Composite scoring](https://docs.typesafe.ai/patterns/composite-scoring) | ideas for Exercise 3 / final challenge | ✅ |
| [Speculative fan-out](https://docs.typesafe.ai/patterns/fan-out) | why 3 questions share 1 request | ✅ |
| [Example use cases](https://docs.typesafe.ai/concepts/use-case-map) | picking a final-challenge domain | ✅ |

## 5. Cookbooks (after the course)

| Resource | Why read it next | |
|---|---|---|
| [All cookbooks](https://docs.typesafe.ai/cookbooks) | index | ✅ |
| [Function calling](https://docs.typesafe.ai/cookbooks/function_calling) | Jev choosing typed function calls | ✅ |
| [LLM guardrails](https://docs.typesafe.ai/cookbooks/llm_guardrails) | Jev + LLM together (slide 17/20 nuance) | ✅ |
| [Hierarchical classification](https://docs.typesafe.ai/cookbooks/hierarchical_classification) | many categories (Jev supports up to 255 options per Choice) | ✅ |
| [Classification using confidence](https://docs.typesafe.ai/cookbooks/classification_using_confidence) | fallback to a broader class when unsure | ✅ |
| [Classifying RAG passages](https://docs.typesafe.ai/cookbooks/classifying_rag_passages) | filtering retrieved text | ✅ |
| [Citation checking](https://docs.typesafe.ai/cookbooks/citation_check) | verifying claims against sources | ✅ |
| [Simple memory system](https://docs.typesafe.ai/cookbooks/basic_memory) | — | ⚠️ not in the official index |
| [Smart home demo](https://docs.typesafe.ai/demos/smart-home) | a complete working app | ✅ |

## 6. Production & limitations (Modules 8–9)

| Resource | Course connection | |
|---|---|---|
| [Jev 1.13 known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) | **required reading**: numbers, dates, literal reading, option order, adversarial state | ✅ |
| [Python retry policies](https://docs.typesafe.ai/sdk/python/api/retries) | `RetryPolicy` config in `jev_client.py` | ✅ |
| [Python SDK changelog](https://docs.typesafe.ai/sdk/python/changelog) | check before upgrading from 0.7.4 | ✅ |
| [Agent skill](https://docs.typesafe.ai/agent-skill) | using Jev from coding agents | ✅ |

## 7. Independent tutorials (third-party, not verified)

| Resource | Topic | |
|---|---|---|
| [Jev API quickstart](https://www.typesafeai.org/guides/jev-api-quickstart) | first call | 🔸 |
| [Jev with Python](https://www.typesafeai.org/guides/jev-python) | Python usage | 🔸 |
| [Jev with TypeScript](https://www.typesafeai.org/guides/jev-typescript) | TypeScript usage | 🔸 |
| [Choice, Score, and Noul](https://www.typesafeai.org/guides/choice-score-noul) | primitives | 🔸 |
| [Jev limitations](https://www.typesafeai.org/guides/jev-limitations) | limitations | 🔸 |
| [Community projects](https://www.typesafeai.org/cases) | examples | 🔸 |

## Official pages not in the PDF, used by this course

| Resource | Why |
|---|---|
| [Advanced: structure](https://docs.typesafe.ai/primitives/advanced) | structured `instructions`/`criteria` |
| [Date extraction cookbook](https://docs.typesafe.ai/cookbooks/date_extraction_cookbook) | the "compute dates in code" rule behind slide 27's correction |
| [Self-consistency: choices](https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook) | agreement vs. automation share, related to the Module 8 threshold sweep |
| [Legal](https://docs.typesafe.ai/legal) | data processing, retention, ZDR — production checklist |
| [Python SDK source](https://github.com/typesafe-ai/typesafe-sdk-python) | reading the SDK itself |
