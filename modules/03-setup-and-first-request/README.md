# Module 3 — Setup & Your First Request

⏱ 12:00–20:00 · ⬅ [Module 2](../02-jev-fundamentals/README.md) · Next ➡ [Module 4](../04-classification-with-jev/README.md)

**Goal:** a working environment and one real, authenticated Jev response on your screen.

**Slides:** page 24 of [jev-slides.pdf](../01-introduction-and-resources/materials/jev-slides.pdf). Its Python code is correct; you'll run the same idea.

## Set up

**macOS / Linux**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```
**Windows (PowerShell)**
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Put your key in `.env` as `TYPESAFE_API_KEY=...` (from the [console](https://console.typesafe.ai/keys)).
`.env` is git-ignored: never commit it or show it on screen. No key? Set `JEV_BACKEND=mock` and add
`--offline` to examples.

```bash
pytest -q          # expect: 98 passed, 1 skipped
```

## First request

```bash
python examples/01_first_request.py            # live
python examples/01_first_request.py --offline  # mock (labelled)
```

## Files

| File | What it teaches |
|---|---|
| [`.env.example`](../../.env.example) | every setting, with safe defaults |
| [`examples/_common.py`](../../examples/_common.py) | live vs. offline; reads your key from `.env` as a `SecretStr` |
| [`examples/01_first_request.py`](../../examples/01_first_request.py) | state → questions → `TypeSafeClient` → `system_one()` → typed answers → raw JSON |

**Look at:** `model` (versioned id), `choice`, `probabilities`, `confidence`, `noul`, `usage.input_tokens`.

## Failure case to try

Blank the key in `.env` and run again:
```text
Client setup failed: No API key was provided. Pass api_key or set the TYPESAFE_API_KEY environment variable.
```
Then try a wrong key to see the 401 branch. Note the `except` order: specific errors first.

## Reading

[Quick start](https://docs.typesafe.ai/introduction/quickstart) ·
[Python SDK](https://docs.typesafe.ai/sdk/python) ·
[Sync client](https://docs.typesafe.ai/sdk/python/api/clients/sync) ·
[Exceptions](https://docs.typesafe.ai/sdk/python/api/exceptions)

## ✅ Checkpoint

`pytest` passes, you've seen one real response, and you can say where your key lives and why it's safe.

Next ➡ [Module 4 — Classification with Jev](../04-classification-with-jev/README.md)
