# Continuous integration (GitHub Actions)

Every time someone pushes to `main` or opens a pull request, GitHub runs this project's checks on its
own machines and shows a result: ✅ everything passed, or ❌ something broke. The workflow lives in
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

## Why it matters

- **Breakages show up immediately.** If a change, yours or a learner's pull request, breaks the code
  style or a test, you see a red ❌ before anyone else hits the problem.
- **It proves the project works on more than one machine.** CI tests on Linux with Python 3.11, 3.12
  and 3.13, and on Windows, where most learners run the course.
- **The badge in the README** tells visitors at a glance that the project currently passes.

## What runs

Four jobs run in parallel, one per row:

| Operating system | Python |
|---|---|
| Ubuntu (Linux) | 3.11 |
| Ubuntu (Linux) | 3.12 |
| Ubuntu (Linux) | 3.13 |
| Windows | 3.13 |

Each job does exactly what you do locally:

1. **Check out the code.**
2. **Set up Python** (with pip caching, so later runs are faster).
3. **Install the project:** `pip install -e ".[dev,ui]"`
4. **Code style:** `ruff format --check .` and `ruff check .`
5. **Tests:** `pytest -q`, which should give **103 passed, 1 skipped**.

## No API key, on purpose

CI needs **no secrets**. The tests drive the real TypeSafe SDK through a mocked network, so they never
call Jev. The one live test skips itself unless `RUN_LIVE_TESTS=1` is set, and CI doesn't set it.

**Never add your TypeSafe API key to GitHub** (not as a secret, not in a file). Run the live test on your
own machine instead:

```powershell
$env:RUN_LIVE_TESTS = "1"; pytest -m live -s
Remove-Item Env:RUN_LIVE_TESTS
```

## When it runs

- on every **push to `main`**;
- on every **pull request**;
- **manually**: open the **Actions** tab, choose **CI**, then **Run workflow**.

If you push again while a run is still going, the older run is cancelled automatically.

## Reading the results

1. Open the repository on GitHub and click the **Actions** tab.
2. Click a run to see its four jobs. Green ✅ means passed; red ❌ means failed.
3. Click a failed job, then the red step, to see the exact error, just like in your own terminal.

## Run the same checks locally before pushing

```bash
ruff format --check .
ruff check .
pytest -q
```

If formatting fails, `ruff format .` fixes it automatically. Then run the checks again and push.

## Common failures

| What fails | Usual cause | Fix |
|---|---|---|
| Code style | a file isn't formatted | run `ruff format .`, commit, push |
| Tests on all four jobs | a real bug in the change | run `pytest -q` locally and fix the failing test |
| Tests only on Windows | path or line-ending assumptions | use `pathlib.Path`, avoid hard-coded `/` paths |
| Tests only on Python 3.11 | a newer-Python-only feature | use syntax supported by 3.11 (the minimum in `pyproject.toml`) |
| Install step | a dependency release broke something | pin the version in `pyproject.toml` |

## Cost

Free for **public** repositories. Private repositories get a free monthly allowance of minutes, which is
far more than this workflow needs.
