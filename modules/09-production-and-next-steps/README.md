# Module 9 — Production Hardening & Next Steps

⏱ 68:00–75:00 · ⬅ [Module 8](../08-testing-and-evaluation/README.md) · 🏠 [Course home](../../README.md)

**Goal:** see what makes this production-oriented, what's still missing, and apply the pattern on your own.

**Slides:** pages 27–29 of [jev-slides.pdf](../01-introduction-and-resources/materials/jev-slides.pdf): suspicious logins, complaints,
invoices, feedback. (Page 26, email priority, was introduced in Module 4; example 05 revisits it.)

## Business scenarios, built correctly

```bash
python examples/05_business_patterns.py
```
[`examples/05_business_patterns.py`](../../examples/05_business_patterns.py) rebuilds the slides'
scenarios. The pattern the slides don't show: the login hour, the known-country check and the
invoice amount limit are computed **in Python**, and Jev gets the results as named facts.

## Production tour

| Concern | Where |
|---|---|
| secrets (`SecretStr`), env-driven thresholds | [`app/config.py`](../../app/config.py), [`.env.example`](../../.env.example) |
| JSON logs, no message text; SDK logger kept at WARNING | [`app/utils/logging.py`](../../app/utils/logging.py) |
| PII redaction before Jev and the database | [`app/utils/privacy.py`](../../app/utils/privacy.py) |
| timeouts, retry budget | [`app/services/jev_client.py`](../../app/services/jev_client.py) |
| health check that doesn't spend Jev quota; metrics | [`app/api/routes.py`](../../app/api/routes.py) |
| container: non-root, healthcheck, single worker (SQLite) | [`Dockerfile`](../../Dockerfile) |

```bash
docker build -t practical-jev-ai .
docker run --rm -p 8000:8000 --env-file .env -e DATABASE_URL=sqlite:////data/tickets.db -v jevdata:/data practical-jev-ai
```

**Before real traffic**, read [docs/production-checklist.md](../../docs/production-checklist.md): authentication,
Postgres + migrations, a real PII service, an outbox for downstream actions, thresholds tuned on your
own data, and pinning `JEV_MODEL=jev-1.13.0`.

## Exercises

From [docs/student-guide.md](../../docs/student-guide.md):
1. **Add the `shipping` category** (slides 25, 28).
2. **Change the confidence policy** and compare coverage vs. accuracy.
3. **Add a sentiment question** and expose it through the API.

**Final challenge:** rebuild the architecture for another domain (issue triage, document intake,
content moderation).

## Keep learning

[Cookbooks](https://docs.typesafe.ai/cookbooks) ·
[LLM guardrails](https://docs.typesafe.ai/cookbooks/llm_guardrails) ·
[Function calling](https://docs.typesafe.ai/cookbooks/function_calling) ·
[SDK changelog](https://docs.typesafe.ai/sdk/python/changelog) — full list in [learning-resources.md](../01-introduction-and-resources/learning-resources.md).

## Recap

*Jev makes the judgment; your code decides what to do with it.*

🏁 End of course · back to [Module 1](../01-introduction-and-resources/README.md) · [Course home](../../README.md)
