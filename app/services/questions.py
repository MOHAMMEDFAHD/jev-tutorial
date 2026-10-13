"""The decision problem we ask Jev, defined with the official SDK question types.

Design notes (from TypeSafe's docs, see docs/architecture.md for links):
* Three decisions: department (Choice), priority (Score) and human review. Human review is
  answered by FOUR narrow yes/no checks (Nouls) rather than one combined question; our code
  then applies "any check likely -> a person" (TypeSafe: use one Noul per label when several
  may apply). All questions go in ONE request and are evaluated in parallel against the
  same state, so the extra checks barely change latency.
* Jev reads instructions literally, so criteria spell out boundary cases explicitly.
* Question keys ("department", ...) are NOT sent to the model; only instructions/criteria are.
* Choice option order can bias jev-1.13 toward the first option; evaluate with your data.
"""

from typesafe_sdk import Choice, Noul, Score

from app.models.decision import Department, Priority

DEPARTMENT_KEY = "department"
PRIORITY_KEY = "priority"
HUMAN_REVIEW_PREFIX = "needs_human_"  # question keys look like "needs_human_legal_threat"

DEPARTMENT_CRITERIA: dict[str, str] = {
    Department.BILLING: (
        "Charges, invoices, payment methods, refunds, double charges, or billing errors "
        "on an existing subscription."
    ),
    Department.TECHNICAL: (
        "Bugs, errors, outages, crashes, slow performance, integrations or API problems "
        "with the product."
    ),
    Department.ACCOUNT: (
        "Logging in, passwords, two-factor authentication, locked or compromised accounts, "
        "changing account owner or email, or closing/cancelling an account or subscription."
    ),
    Department.SALES: (
        "Pricing questions, plan comparisons, upgrades, quotes, or buying for a new team "
        "before purchase."
    ),
    Department.GENERAL: (
        "Anything that does not clearly fit billing, technical, account, or sales, "
        "including feedback and general questions."
    ),
}

# Score levels are ordered from 0 (index of the first item) upward.
PRIORITY_CRITERIA: list[str] = [
    "low: a question or minor request with no impact on the customer's work",
    "medium: a problem that inconveniences the customer but has a workaround",
    "high: the customer is blocked, losing money, or charged incorrectly, and needs help today",
    "critical: a security incident, data loss, or a total outage affecting the customer's business",
]
assert [level.split(":")[0] for level in PRIORITY_CRITERIA] == [p.value for p in Priority]

# Decision C: four narrow yes/no checks. Each answers ONE condition; the policy sends the
# ticket to a person if ANY of them is likely. The name of each check becomes the reason
# a reviewer sees, e.g. "needs_human:legal_threat".
HUMAN_REVIEW_CHECKS: dict[str, str] = {
    "legal_threat": (
        "Does the customer threaten legal action, or say they will involve a lawyer, a court "
        "or a regulator?"
    ),
    "fraud_or_takeover": (
        "Does the customer report fraud, stolen payment details, or that someone else has "
        "accessed or taken over their account? A billing mistake such as a double charge "
        "is not fraud."
    ),
    "compensation_request": (
        "Does the customer ask for compensation beyond refunding a charge, such as credits, "
        "damages, or payment for lost business?"
    ),
    "manager_request": (
        "Does the customer ask to speak to a manager, a supervisor, or someone more senior?"
    ),
}


def build_ticket_questions() -> dict[str, Choice | Score | Noul]:
    """Return every question sent with a ticket: Choice + Score + four Nouls, in ONE request."""
    return {
        DEPARTMENT_KEY: Choice(
            instructions="Which support department should handle this customer message?",
            criteria=dict(DEPARTMENT_CRITERIA),
        ),
        PRIORITY_KEY: Score(
            instructions="How urgent is this customer message?",
            criteria=list(PRIORITY_CRITERIA),
        ),
        **{
            HUMAN_REVIEW_PREFIX + name: Noul(instructions=instructions)
            for name, instructions in HUMAN_REVIEW_CHECKS.items()
        },
    }


def build_state(message: str) -> dict[str, str]:
    """Wrap the (already sanitized) message as structured state.

    Only the message is sent: TypeSafe notes accuracy drops when state contains
    irrelevant detail, and sending less customer data is better for privacy.
    """
    return {"customer_message": message}
