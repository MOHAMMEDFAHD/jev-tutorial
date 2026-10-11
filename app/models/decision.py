"""The APPLICATION's typed decision schema.

These models are ours, not TypeSafe's. Jev returns native answers
(ChoiceAnswer / ScoreAnswer / NoulAnswer from typesafe_sdk); app/services/decision_parser.py
validates those and converts them into the models below. Keeping the two separate means
an SDK or API change breaks in exactly one place: the parser.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Department(StrEnum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    SALES = "sales"
    GENERAL = "general"


class Priority(StrEnum):
    """Ordered: the Score level index is the position in this list (low=0 ... critical=3)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_level(cls, level: int) -> "Priority":
        return list(cls)[level]


class Action(StrEnum):
    AUTO_ROUTE = "auto_route"
    HUMAN_REVIEW = "human_review"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class DepartmentDecision(_Frozen):
    """Decision A: which team handles the ticket (Jev Choice)."""

    department: Department
    confidence: float = Field(ge=0, le=1)  # returned by Jev
    probabilities: dict[Department, float]  # returned by Jev
    top2_margin: float = Field(ge=0, le=1)  # computed by us: p(top) - p(runner-up)


class PriorityDecision(_Frozen):
    """Decision B: how urgent the ticket is (Jev Score over 4 ordered levels)."""

    priority: Priority  # most likely level (argmax), computed by us
    expected_score: float = Field(ge=0, le=3)  # Jev's probability-weighted score
    confidence: float = Field(ge=0, le=1)  # returned by Jev
    probabilities: dict[Priority, float]  # returned by Jev (re-keyed by us)


class HumanReviewSignal(_Frozen):
    """Decision C: does this need a human? (Jev Noul = probability that the answer is yes)."""

    probability: float = Field(ge=0, le=1)


class TicketDecision(_Frozen):
    """Everything Jev told us about one ticket, validated and typed."""

    department: DepartmentDecision
    priority: PriorityDecision
    human_review: HumanReviewSignal
    model: str  # versioned model id reported by the API, e.g. "jev-1.13.0"
    request_id: str | None = None
    input_tokens: int | None = None


class PolicyOutcome(_Frozen):
    """Decision D: what the application does. Produced by Python rules, not by the model."""

    action: Action
    queue: str
    reasons: list[str]  # every rule that fired, for audit and for reviewers
