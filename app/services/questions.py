"""The decision problem we ask Jev, defined with the official SDK question types.

Design notes (from TypeSafe's docs, see docs/architecture.md for links):
* One atomic question per decision. All three go in ONE request and are evaluated
  in parallel against the same state, so adding a question barely changes latency.
* Jev reads instructions literally, so criteria spell out boundary cases explicitly.
* Question keys ("department", ...) are NOT sent to the model; only instructions/criteria are.
* Choice option order can bias jev-1.13 toward the first option; evaluate with your data.
"""

from typesafe_sdk import Choice, Noul, Score

from app.models.decision import Department, Priority

DEPARTMENT_KEY = "department"
PRIORITY_KEY = "priority"
HUMAN_REVIEW_KEY = "needs_human"

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

HUMAN_REVIEW_INSTRUCTIONS = (
    "Does this message require a human support agent rather than an automated workflow? "
    "Answer yes if it contains a legal threat, a request for compensation beyond a standard "
    "refund, a report of fraud or account takeover, or a request to speak to a manager."
)


def build_ticket_questions() -> dict[str, Choice | Score | Noul]:
    """Return the three questions sent with every ticket (one request, parallel evaluation)."""
    return {
        DEPARTMENT_KEY: Choice(
            instructions="Which support department should handle this customer message?",
            criteria=dict(DEPARTMENT_CRITERIA),
        ),
        PRIORITY_KEY: Score(
            instructions="How urgent is this customer message?",
            criteria=list(PRIORITY_CRITERIA),
        ),
        HUMAN_REVIEW_KEY: Noul(instructions=HUMAN_REVIEW_INSTRUCTIONS),
    }


def build_state(message: str) -> dict[str, str]:
    """Wrap the (already sanitized) message as structured state.

    Only the message is sent: TypeSafe notes accuracy drops when state contains
    irrelevant detail, and sending less customer data is better for privacy.
    """
    return {"customer_message": message}
