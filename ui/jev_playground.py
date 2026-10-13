"""Jev playground: type a support message, see Jev's decision and what our policy does with it.

Run from the repository root (so .env is found):

    pip install -e ".[ui]"
    streamlit run ui/jev_playground.py

It uses exactly the same pieces as the API server: the ticket questions, the response
validation (decision_parser), the automation policy and the router. Moving a policy
slider re-applies the rules to the answer you already have, so it never calls Jev again.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable

from typesafe_sdk import TypeSafeClient, TypeSafeError

from app.config import Settings
from app.models.decision import Action, Priority, TicketDecision
from app.policies.automation_policy import AutomationPolicy, Reason
from app.services.decision_parser import parse_ticket_decision
from app.services.jev_client import JevError, to_jev_error
from app.services.mock_backend import MOCK_API_KEY, mock_transport
from app.services.questions import build_state, build_ticket_questions
from app.services.routing_service import route_ticket
from app.utils.privacy import redact_pii

LIVE = "Live Jev (uses your API key)"
MOCK = "Offline mock (no key, not Jev)"
DATASET = Path(__file__).resolve().parents[1] / "evaluation" / "sample_tickets.json"

QUEUE_NAMES = {
    "billing_queue": "billing queue",
    "technical_queue": "technical queue",
    "account_queue": "account queue",
    "sales_queue": "sales queue",
    "general_queue": "general queue",
    "human_review_queue": "human review queue",
    "escalation_queue": "escalation queue (senior agent)",
}

CHECK_LABELS = {
    "legal_threat": "a legal threat",
    "fraud_or_takeover": "fraud or an account takeover",
    "compensation_request": "a request for compensation beyond a refund",
    "manager_request": "a request to speak to a manager",
}

FAILURE_TEXT = {
    "jev_auth_failed": "Jev rejected the API key. Check TYPESAFE_API_KEY in your .env file.",
    "jev_rate_limited": "Jev is rate limiting requests. Wait a few seconds and try again.",
    "jev_timeout": "Jev didn't answer in time. Try again, or raise JEV_TIMEOUT_SECONDS.",
    "jev_unavailable": "Couldn't reach Jev. Check your internet connection, VPN or proxy.",
    "jev_bad_request": "Jev rejected the request. The message may be empty or too long.",
    "jev_invalid_response": "Jev's answer was missing fields, so it wasn't trusted.",
    "decision_validation_failed": "Jev's answer failed our checks, so it wasn't trusted.",
}

CSS = """
<style>
.verdict { border-radius: 14px; padding: 1.1rem 1.4rem; margin: 0.4rem 0 1.2rem; }
.verdict h2 { margin: 0 0 0.35rem; font-size: 1.6rem; line-height: 1.25; }
.verdict p { margin: 0.15rem 0; }
.verdict.auto { background: #E4F4EC; border-left: 7px solid #1F8A5B; }
.verdict.review { background: #FDF0E1; border-left: 7px solid #C2620C; }
.verdict.failed { background: #FBE7E7; border-left: 7px solid #B42318; }
.chosen { font-weight: 700; }
</style>
"""


# ---- Calling Jev ---------------------------------------------------------------------
@dataclass
class JevCall:
    decision: TicketDecision | None
    raw: dict | None
    latency_ms: float | None
    sent_text: str
    error: JevError | None = None
    at: datetime = field(default_factory=datetime.now)


@st.cache_resource(show_spinner=False)
def get_client(backend: str) -> TypeSafeClient:
    """One client per backend, kept open between requests so calls stay fast."""
    settings = Settings()
    common = {"model": settings.jev_model, "timeout": settings.jev_timeout_seconds}
    if backend == MOCK:
        return TypeSafeClient(api_key=MOCK_API_KEY, transport=mock_transport(), **common)
    if settings.typesafe_api_key is None:
        raise ValueError("TYPESAFE_API_KEY is not set in .env")
    return TypeSafeClient(api_key=settings.typesafe_api_key.get_secret_value(), **common)


def ask_jev(message: str, backend: str) -> JevCall:
    sent = redact_pii(message)  # same privacy step as the API server
    started = time.perf_counter()
    try:
        response = get_client(backend).system_one(
            state=build_state(sent), questions=build_ticket_questions()
        )
        decision = parse_ticket_decision(response)
    except TypeSafeError as exc:
        return JevCall(None, None, None, sent, error=to_jev_error(exc))
    except JevError as exc:  # our own validation rejected the answer
        return JevCall(None, None, None, sent, error=exc)
    latency = (time.perf_counter() - started) * 1000
    return JevCall(decision, response.raw_http_response.json(), latency, sent)


# ---- Explaining the policy -------------------------------------------------------------
def explain(reason: str, d: TicketDecision, p: AutomationPolicy) -> str:
    if reason.startswith(Reason.HUMAN_REQUESTED + ":"):
        name = reason.split(":", 1)[1]
        prob = d.human_review.checks.get(name, d.human_review.probability)
        return (
            f"Jev sees {CHECK_LABELS.get(name, name)} ({prob:.0%}; "
            f"a person steps in at {p.human_review_noul_threshold:.0%})."
        )
    texts = {
        Reason.ALL_CHECKS_PASSED: "Every check passed, so no person is needed.",
        Reason.MANDATORY_PRIORITY: (
            f"{d.priority.priority.value.capitalize()} tickets always go to a person."
        ),
        Reason.CRITICAL_RISK: (
            f"The chance this is critical is {d.priority.probabilities[Priority.CRITICAL]:.0%} "
            f"(the limit is {p.critical_escalation_probability:.0%})."
        ),
        Reason.LOW_DEPARTMENT_CONFIDENCE: (
            f"Department confidence is {d.department.confidence:.2f}, "
            f"below the {p.auto_route_min_confidence:.2f} needed to route automatically."
        ),
        Reason.AMBIGUOUS_DEPARTMENT: (
            f"The top two departments are only {d.department.top2_margin:.2f} apart "
            f"(at least {p.min_top2_margin:.2f} is needed)."
        ),
        Reason.LOW_PRIORITY_CONFIDENCE: (
            f"Priority confidence is {d.priority.confidence:.2f}, "
            f"below {p.priority_min_confidence:.2f}, so the urgency is unclear."
        ),
    }
    return texts.get(reason, reason)


def policy_from_sidebar(settings: Settings) -> AutomationPolicy:
    st.sidebar.subheader("Policy")
    st.sidebar.caption("Your rules, not Jev's. Changing them re-checks the last answer instantly.")
    return AutomationPolicy(
        auto_route_min_confidence=st.sidebar.slider(
            "Department confidence needed", 0.0, 1.0, settings.auto_route_min_confidence, 0.05
        ),
        min_top2_margin=st.sidebar.slider(
            "Gap between top two departments", 0.0, 1.0, settings.min_top2_margin, 0.05
        ),
        priority_min_confidence=st.sidebar.slider(
            "Priority confidence needed", 0.0, 1.0, settings.priority_min_confidence, 0.05
        ),
        human_review_noul_threshold=st.sidebar.slider(
            "Send to a person when Jev's 'needs a person' is at least",
            0.0,
            1.0,
            settings.human_review_noul_threshold,
            0.05,
        ),
        critical_escalation_probability=st.sidebar.slider(
            "Escalate when chance of critical is at least",
            0.0,
            1.0,
            settings.critical_escalation_probability,
            0.05,
        ),
        mandatory_review_priorities=frozenset(
            Priority(p)
            for p in st.sidebar.multiselect(
                "Always send these priorities to a person",
                [p.value for p in Priority],
                default=list(settings.mandatory_review_priorities),
            )
        ),
    )


# ---- Rendering ---------------------------------------------------------------------------
def show_bars(title: str, probs: dict, chosen) -> None:
    st.markdown(f"**{title}**")
    for option, p in sorted(probs.items(), key=lambda kv: -kv[1]):
        name = option.value if hasattr(option, "value") else str(option)
        css = "chosen" if option == chosen else ""
        st.markdown(f'<span class="{css}">{name}</span> &nbsp; {p:.0%}', unsafe_allow_html=True)
        st.progress(min(max(float(p), 0.0), 1.0))


def show_verdict(call: JevCall, policy: AutomationPolicy) -> None:
    if call.error is not None:
        reason = call.error.reason
        st.markdown(
            f'<div class="verdict failed"><h2>Held for a person: Jev gave no usable answer</h2>'
            f"<p>{FAILURE_TEXT.get(reason, reason)}</p>"
            "<p>In the real service the ticket is still saved and sent to the human review "
            "queue, so nothing is lost.</p></div>",
            unsafe_allow_html=True,
        )
        return

    d = call.decision
    action, reasons = policy.evaluate(d)
    queue = QUEUE_NAMES.get(route_ticket(d, action), route_ticket(d, action))
    if action is Action.AUTO_ROUTE:
        headline, css = f"Routed automatically to the {queue}", "auto"
    else:
        headline, css = f"Held for a person in the {queue}", "review"
    items = "".join(f"<p>• {explain(r, d, policy)}</p>" for r in reasons)
    st.markdown(
        f'<div class="verdict {css}"><h2>{headline}</h2>{items}</div>', unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        show_bars("Department (Choice)", d.department.probabilities, d.department.department)
        st.caption(f"Confidence {d.department.confidence:.2f}")
    with col2:
        show_bars("Priority (Score)", d.priority.probabilities, d.priority.priority)
        st.caption(
            f"Confidence {d.priority.confidence:.2f} · expected level "
            f"{d.priority.expected_score:.2f} of 3"
        )
    with col3:
        st.markdown("**Needs a person? (4 Noul checks)**")
        for name, prob in d.human_review.checks.items():
            label = CHECK_LABELS.get(name, name)
            fired = prob >= policy.human_review_noul_threshold
            st.markdown(
                f'<span class="{"chosen" if fired else ""}">{label}</span> &nbsp; {prob:.0%}',
                unsafe_allow_html=True,
            )
            st.progress(prob)

    with st.expander("Details: model, timing and the raw answer"):
        st.write(f"Model: `{d.model}`")
        st.write(f"Time: {call.latency_ms:.0f} ms" if call.latency_ms else "Time: n/a")
        if d.request_id:
            st.write(f"TypeSafe request id: `{d.request_id}`")
        if d.input_tokens is not None:
            st.write(f"Input tokens: {d.input_tokens}")
        st.write("Text sent to Jev (after removing emails, card and phone numbers):")
        st.code(call.sent_text, language=None)
        st.json(call.raw)


@st.cache_data
def load_examples() -> list[dict]:
    return json.loads(DATASET.read_text(encoding="utf-8"))["tickets"]


def use_example() -> None:
    choice = st.session_state.example_choice
    if choice:
        st.session_state.message = st.session_state.examples_by_label[choice]["message"]


# ---- Page --------------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Jev playground", page_icon="🧭", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    settings = Settings()

    st.sidebar.subheader("Connection")
    default = 0 if settings.typesafe_api_key else 1
    backend = st.sidebar.radio("Answers come from", [LIVE, MOCK], index=default, key="backend")
    if backend == MOCK:
        st.sidebar.warning("Offline mock: answers come from a keyword rule, not from Jev.")
    elif settings.typesafe_api_key is None:
        st.sidebar.error("No TYPESAFE_API_KEY in .env. Add it, or switch to the offline mock.")
    policy = policy_from_sidebar(settings)

    st.title("Jev ticket triage")
    st.write(
        "Type a customer message. Jev decides the department, the priority and whether a "
        "person is needed; your policy decides what happens next."
    )

    examples = load_examples()
    st.session_state.examples_by_label = {
        f"{t['message'][:70]}{'…' if len(t['message']) > 70 else ''}": t for t in examples
    }
    st.selectbox(
        "Start from an example (optional)",
        [""] + list(st.session_state.examples_by_label),
        key="example_choice",
        on_change=use_example,
    )

    with st.form("ask"):
        message = st.text_area(
            "Customer message",
            key="message",
            height=110,
            max_chars=settings.max_message_chars,
            placeholder="I was charged twice for my subscription and need a refund.",
        )
        submitted = st.form_submit_button("Decide", type="primary")

    if submitted:
        if not message.strip():
            st.info("Type a message first, then press Decide.")
        elif backend == LIVE and settings.typesafe_api_key is None:
            st.info("Add TYPESAFE_API_KEY to .env, then restart, or switch to the offline mock.")
        else:
            with st.spinner("Asking Jev…"):
                call = ask_jev(message, backend)
            st.session_state.last = call
            st.session_state.setdefault("history", []).insert(0, (message, backend, call))

    last: JevCall | None = st.session_state.get("last")
    if last is not None:
        show_verdict(last, policy)

    history = st.session_state.get("history", [])
    if history:
        st.subheader("This session")
        rows = []
        for msg, src, call in history:
            d = call.decision
            action = policy.evaluate(d)[0].value.replace("_", " ") if d else "failed"
            rows.append(
                {
                    "time": call.at.strftime("%H:%M:%S"),
                    "message": msg[:60] + ("…" if len(msg) > 60 else ""),
                    "department": d.department.department.value if d else "",
                    "confidence": round(d.department.confidence, 2) if d else None,
                    "priority": d.priority.priority.value if d else "",
                    "action (current policy)": action,
                    "ms": round(call.latency_ms) if call.latency_ms else None,
                    "source": "Jev" if src == LIVE else "mock",
                }
            )
        st.dataframe(rows, hide_index=True, width="stretch")


main()
