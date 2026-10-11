"""Module 9 - the slide deck's business scenarios, built with the real API.

The deck (slides 26-29) shows four scenarios. This file implements each one correctly:

  1. Email prioritization   -> Score (ordered levels), not Choice
  2. Suspicious login       -> Noul, with time/location facts computed IN CODE first
  3. Invoice review         -> Noul + a numeric rule kept in code (Jev isn't a calculator)
  4. Customer feedback      -> Choice (sentiment)

Rules applied from TypeSafe's jev-1.13 limitations page:
  * arithmetic, thresholds, and date/time comparison happen in Python;
  * Jev gets the RESULT as a named fact (e.g. "login_hour_is_unusual": True);
  * Jev predicts; our code decides the action.

Each scenario judges a different input, so each gets its own request. Questions about
the SAME input belong together in one request (see app/services/questions.py).

Run:  python examples/05_business_patterns.py [--offline]
"""

from datetime import datetime

from _common import client_kwargs, parse_offline_flag
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

offline = parse_offline_flag(__doc__)


def show(title: str, decided: str, detail: str) -> None:
    print(f"\n== {title}\n   {detail}\n   -> ACTION (decided by our code): {decided}")


with TypeSafeClient(**client_kwargs(offline)) as client:
    # 1. Email prioritization (slide 26). Ordered levels => Score.
    email = "Subject: Server is down! Our production server is down. Customers cannot access the website!"
    r = client.system_one(
        state={"email": email},
        questions={
            "priority": Score(
                instructions="How urgently does this email need a response?",
                criteria=[
                    "low: no action needed soon",
                    "normal: respond within a day",
                    "urgent: production impact, respond now",
                ],
            )
        },
    )
    p = r.scores["priority"]
    level = max(p.probabilities, key=p.probabilities.get)
    action = "page on-call engineer" if level == 2 and p.confidence >= 0.5 else "normal inbox"
    show(
        "Email prioritization (Score)",
        action,
        f"most likely level={level} ({p.legend[level][:20]}...), expected score={p.score:.2f}, "
        f"confidence={p.confidence:.2f}",
    )

    # 2. Suspicious login (slide 27). Compute facts in code; ask Jev only the judgment.
    login_hour, usual_hours = 2, range(7, 23)
    known_countries = {"US"}
    facts = {
        "device_seen_before": False,
        "country_seen_before": "RU" in known_countries,  # code, not the model
        "login_hour_is_unusual": login_hour not in usual_hours,  # code, not the model
        "password_correct": True,
    }
    r = client.system_one(
        state={"login_attempt": facts},
        questions={
            "suspicious": Noul(
                instructions="Does this login attempt look like account takeover rather than "
                "the account owner on a new device?"
            )
        },
    )
    p_susp = r.nouls["suspicious"].noul
    action = "require verification code" if p_susp >= 0.3 else "allow"  # low bar: cheap step-up
    show("Suspicious login (Noul)", action, f"facts={facts} -> P(suspicious)={p_susp:.2f}")

    # 3. Invoice review (slide 29). The amount rule is arithmetic -> code. Jev judges text.
    invoice = {
        "vendor": "Acme Supplies",
        "amount": 12_500.00,
        "po_number": None,
        "line_items": "Consulting services, misc.",
    }
    over_limit = invoice["amount"] > 10_000  # deterministic business rule
    r = client.system_one(
        state={"invoice": invoice},
        questions={
            "vague_items": Noul(
                instructions="Are the invoice line items too vague to verify what was purchased?"
            )
        },
    )
    vague = r.nouls["vague_items"].noul >= 0.5
    needs_review = over_limit or vague or invoice["po_number"] is None
    show(
        "Invoice review (Noul + code rules)",
        "send to accounting" if needs_review else "auto-approve",
        f"over_limit={over_limit} (code), missing_po={invoice['po_number'] is None} (code), "
        f"P(vague)={r.nouls['vague_items'].noul:.2f} (Jev)",
    )

    # 4. Customer feedback (slide 29). Unordered labels => Choice.
    r = client.system_one(
        state={"feedback": "Love the new dashboard, but exports are still painfully slow."},
        questions={
            "sentiment": Choice(
                instructions="What is the overall sentiment of this feedback?",
                criteria={
                    "positive": None,
                    "neutral": "mixed or no clear feeling",
                    "negative": None,
                },
            )
        },
    )
    s = r.choices["sentiment"]
    action = f"log to CRM as {s.choice}" if s.confidence >= 0.5 else "log to CRM as 'unclear'"
    show(
        "Customer feedback (Choice)",
        action,
        f"choice={s.choice}, probabilities={s.probabilities}, confidence={s.confidence:.2f}",
    )

print(
    f"\nRun at {datetime.now():%Y-%m-%d %H:%M}; thresholds above are illustrative policy choices."
)
