"""Modules 4-5 - typed decisions: Choice, Score, Noul, and our own application types.

Problem: "the model returned something" isn't good enough. Our code needs to know the
answer is one of OUR departments, a real priority level, a real probability - or fail loudly.

Two layers of typing:
  A. Native (SDK): ChoiceAnswer / ScoreAnswer / NoulAnswer, optionally a response_model.
  B. Application: Department/Priority enums and TicketDecision, built by our parser,
     which rejects anything it can't trust.

Run:  python examples/02_typed_decisions.py [--offline]
"""

import json

from _common import client_kwargs, parse_offline_flag
from typesafe_sdk import (
    ChoiceAnswer,
    NoulAnswer,
    ScoreAnswer,
    SystemOneResponse,
    TypeSafeClient,
)

from app.services.decision_parser import DecisionValidationError, parse_ticket_decision
from app.services.questions import build_state, build_ticket_questions

offline = parse_offline_flag(__doc__)
message = "Our Stripe integration has been failing for 3 days and we're losing sales. Help ASAP."


# --- A. Native typing: declare the answers we expect; the SDK validates the shape. ---------
class TicketAnswers(SystemOneResponse):
    department: ChoiceAnswer  # Choice: pick one option      -> choice, probabilities, confidence
    priority: ScoreAnswer  # Score: rate on ordered levels -> score, probabilities, confidence
    needs_human: NoulAnswer  # Noul: is this true?           -> noul (a probability, no confidence)


with TypeSafeClient(**client_kwargs(offline)) as client:
    response = client.system_one(
        state=build_state(message),
        questions=build_ticket_questions(),
        response_model=TicketAnswers,
    )

print("NATIVE ANSWERS (from the SDK)")
print(f"  department : {response.department.choice!r}  confidence={response.department.confidence}")
print(
    f"  priority   : score={response.priority.score}  probabilities={response.priority.probabilities}"
)
print(f"               legend={response.priority.legend}")
print(f"  needs_human: noul={response.needs_human.noul}")

# --- B. Application typing: convert + validate into OUR schema. ---------------------------
decision = parse_ticket_decision(response)
print("\nAPPLICATION DECISION (our enums, validated)")
print(f"  department : {decision.department.department!r}")
print(f"  priority   : {decision.priority.priority!r}  (most likely level)")
print(f"  top-2 gap  : {decision.department.top2_margin:.2f}")
print(f"  model      : {decision.model}")

# --- Failure case: a label we never defined must be rejected, not passed along. -----------
tampered = response.raw_http_response.json()
tampered["answers"]["department"]["choice"] = "legal"
try:
    parse_ticket_decision(SystemOneResponse.model_validate_json(json.dumps(tampered)))
except DecisionValidationError as err:
    print(f"\nREJECTED tampered response -> {err}")
