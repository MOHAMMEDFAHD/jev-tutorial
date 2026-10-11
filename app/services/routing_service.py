"""Turn (decision, policy action) into a destination queue.

Routing never overrides the policy: if the policy says HUMAN_REVIEW the ticket goes to a
human queue, whatever the department. Unknown or missing departments fall back to the
general queue rather than raising - a ticket must always land somewhere.
"""

from app.models.decision import Action, Department, Priority, TicketDecision

DEPARTMENT_QUEUES: dict[Department, str] = {
    Department.BILLING: "billing_queue",
    Department.TECHNICAL: "technical_queue",
    Department.ACCOUNT: "account_queue",
    Department.SALES: "sales_queue",
    Department.GENERAL: "general_queue",
}
FALLBACK_QUEUE = "general_queue"
HUMAN_REVIEW_QUEUE = "human_review_queue"
ESCALATION_QUEUE = "escalation_queue"   # reviewed by a senior agent first


def route_ticket(decision: TicketDecision | None, action: Action) -> str:
    """Return the queue name for a ticket.

    `decision` is None when Jev could not be reached or returned an invalid response.
    """
    if action is Action.HUMAN_REVIEW or decision is None:
        if decision is not None and decision.priority.priority is Priority.CRITICAL:
            return ESCALATION_QUEUE
        return HUMAN_REVIEW_QUEUE
    return DEPARTMENT_QUEUES.get(decision.department.department, FALLBACK_QUEUE)
