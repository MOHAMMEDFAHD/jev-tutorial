"""Module 6 - the automated routing workflow, end to end, without a web server.

Problem: individual predictions are not a product. We need a workflow that, for every
ticket, either routes it automatically or holds it for a human - and says why.

Pipeline: redact PII -> one Jev call (3 decisions, 6 questions) -> validate -> policy -> route.

Run:  python examples/04_automated_routing.py [--offline]
      With --offline, the last ticket simulates a Jev timeout to show graceful degradation.
"""

import asyncio

from _common import parse_offline_flag

from app.config import Settings
from app.policies.automation_policy import AutomationPolicy
from app.services.decision_service import DecisionService
from app.services.jev_client import build_jev_client
from app.utils.logging import configure_logging
from app.utils.privacy import redact_pii

offline = parse_offline_flag(__doc__)
configure_logging("WARNING")  # JSON log lines; failures are logged, ticket text never is

TICKETS = [
    ("T-1", "I was charged twice for my subscription and need a refund."),
    ("T-2", "Total outage: none of our 400 employees can load the app since 9am."),
    ("T-3", "Someone logged into my account and changed my email. I think I was hacked."),
    ("T-4", "What's the price difference between the Team and Enterprise plans?"),
    ("T-5", "hello??"),
    ("T-6", "Refund me now or my lawyer will be in touch. Card 4111 1111 1111 1111."),
]
if offline:  # failure injection only exists in the mock
    TICKETS.append(("T-7", "Please help [[simulate:timeout]]"))


async def main() -> None:
    settings = Settings(jev_backend="mock") if offline else Settings()
    jev = build_jev_client(settings)  # fails fast with a clear message if no key is set
    service = DecisionService(jev, AutomationPolicy.from_settings(settings))
    try:
        results = await asyncio.gather(
            *(service.process(tid, redact_pii(msg)) for tid, msg in TICKETS)
        )
    finally:
        await jev.aclose()

    print(
        f"{'id':<4} {'department':<10} {'prio':<8} {'conf':>5}  {'action':<12} "
        f"{'queue':<19} reasons"
    )
    for (tid, _), r in zip(TICKETS, results, strict=True):
        d = r.decision
        print(
            f"{tid:<4} {d.department.department.value if d else '-':<10} "
            f"{d.priority.priority.value if d else '-':<8} "
            f"{f'{d.department.confidence:.2f}' if d else '-':>5}  "
            f"{r.action.value:<12} {r.queue:<19} {', '.join(r.reasons)}"
        )

    auto = sum(r.action.value == "auto_route" for r in results)
    print(f"\nautomation coverage: {auto}/{len(results)} tickets routed without a human")


asyncio.run(main())
