"""The local playground UI (ui/jev_playground.py), driven headlessly with Streamlit's AppTest.

Runs against the offline mock; skipped when Streamlit isn't installed (pip install -e ".[ui]").
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

SCRIPT = str(Path(__file__).resolve().parents[1] / "ui" / "jev_playground.py")
MOCK = "Offline mock (no key, not Jev)"


@pytest.fixture
def app(monkeypatch, tmp_path):
    # Run from an empty folder so a developer's real .env (and API key) is never read.
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(SCRIPT, default_timeout=30).run()
    at.radio(key="backend").set_value(MOCK).run()
    return at


def decide(at, message: str):
    at.text_area(key="message").input(message)
    at.button[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    return next(m.value for m in at.markdown if '<div class="verdict' in m.value)


def test_routine_ticket_is_routed_automatically(app):
    verdict = decide(app, "I was charged twice for my subscription and need a refund.")
    assert "Routed automatically to the billing queue" in verdict


def test_policy_slider_rechecks_without_calling_jev_again(app):
    decide(app, "I was charged twice for my subscription and need a refund.")
    app.slider[0].set_value(0.95).run()  # department confidence needed
    verdict = next(m.value for m in app.markdown if '<div class="verdict' in m.value)
    assert "Held for a person" in verdict
    assert len(app.dataframe[0].value) == 1  # still one call in the history


def test_failures_are_explained_not_crashed(app):
    verdict = decide(app, "help [[simulate:timeout]]")
    assert "Jev gave no usable answer" in verdict and "didn't answer in time" in verdict


def test_example_picker_fills_the_message(app):
    label = next(o for o in app.selectbox(key="example_choice").options if o.startswith("Total"))
    app.selectbox(key="example_choice").set_value(label).run()
    assert app.text_area(key="message").value.startswith("Total outage")


def test_live_mode_without_key_says_what_to_do(app):
    app.radio(key="backend").set_value("Live Jev (uses your API key)").run()
    app.text_area(key="message").input("refund please")
    app.button[0].click().run()
    assert any("TYPESAFE_API_KEY" in i.value for i in app.info)
