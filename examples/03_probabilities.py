"""Module 5 - probabilities, confidence, and thresholds.

Problem: a classifier that is right 90% of the time is only automatable if it can tell
you WHICH 10% it's unsure about. Jev returns the full probability distribution; our code
decides how much certainty is enough to act.

Key facts (docs.typesafe.ai/confidence):
  * Choice confidence = (p_max - 1/n) / (1 - 1/n): 0 at an even split, 1 when certain.
  * Noul has no confidence field; |2p - 1| puts it on the same scale.
  * Confidence is NOT the probability of being correct, and never a guarantee.
  * Thresholds are YOUR policy. Tune them on labeled data (evaluation/evaluate.py).

Run:  python examples/03_probabilities.py [--offline]
"""

from _common import client_kwargs, parse_offline_flag
from typesafe_sdk import TypeSafeClient

from app.policies.automation_policy import AutomationPolicy
from app.services.decision_parser import parse_ticket_decision
from app.services.questions import build_state, build_ticket_questions

offline = parse_offline_flag(__doc__)

MESSAGES = {
    "clear": "I was charged twice for my subscription and need a refund.",
    "ambiguous": "Why did my price go up from $20 to $25 without notice?",
    "vague": "hello??",
}


def choice_confidence(probabilities: list[float]) -> float:
    """TypeSafe's published Choice formula, re-implemented to cross-check the API."""
    n = len(probabilities)
    return (max(probabilities) - 1 / n) / (1 - 1 / n)


def bar(p: float, width: int = 30) -> str:
    return "#" * round(p * width)


decisions = {}
with TypeSafeClient(**client_kwargs(offline)) as client:
    for name, message in MESSAGES.items():
        response = client.system_one(state=build_state(message), questions=build_ticket_questions())
        decision = parse_ticket_decision(response)
        decisions[name] = decision
        dept = decision.department
        probs = sorted(dept.probabilities.items(), key=lambda kv: -kv[1])

        print(f"\n[{name}] {message!r}")
        for label, p in probs:
            print(f"   {label.value:<10} {p:5.2f} {bar(p)}")
        recomputed = choice_confidence(list(dept.probabilities.values()))
        ratio = probs[0][1] / probs[1][1] if probs[1][1] > 0 else float("inf")
        human_p = decision.human_review.probability
        print(
            f"   reported confidence {dept.confidence:.3f}   (formula re-computed: {recomputed:.3f})"
        )
        print(
            f"   top probability     {probs[0][1]:.3f}   top-2 margin {dept.top2_margin:.3f}"
            f"   top/second ratio {ratio:.1f}"
        )
        print(
            f"   priority            {decision.priority.priority.value} "
            f"(score {decision.priority.expected_score:.2f}, conf {decision.priority.confidence:.2f})"
        )
        print(
            f"   P(needs human)      {human_p:.2f}   noul confidence |2p-1| = {abs(2 * human_p - 1):.2f}"
        )

# The SAME predictions under three different policies: only our thresholds change.
print("\nSame predictions, different policies (auto_route_min_confidence):")
for threshold in (0.3, 0.6, 0.9):
    policy = AutomationPolicy(auto_route_min_confidence=threshold)
    outcomes = {n: policy.evaluate(d)[0].value for n, d in decisions.items()}
    print(f"   {threshold:.1f}: {outcomes}")
