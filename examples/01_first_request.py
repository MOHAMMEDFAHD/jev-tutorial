"""Module 3 - your first Jev request.

Problem: we want software to decide something about a support message ("is it urgent?",
"which team?") and get back a value our code can branch on - not a paragraph to parse.

Run:  python examples/01_first_request.py            (needs TYPESAFE_API_KEY in .env)
      python examples/01_first_request.py --offline  (no key, mock answers)
"""

import json

from _common import client_kwargs, parse_offline_flag
from typesafe_sdk import (
    Choice,
    Noul,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAuthenticationError,
    TypeSafeClient,
    TypeSafeError,
    TypeSafeRateLimitError,
)

offline = parse_offline_flag(__doc__)

# 1. STATE: the thing we want judged. Plain text works; a dict lets us name fields.
state = {"customer_message": "I was charged twice for my subscription and need a refund."}

# 2. QUESTIONS: a map of names we choose -> typed questions. The names come back as keys.
questions = {
    "is_urgent": Noul(instructions="Does this message express urgency?"),
    "department": Choice(
        instructions="Which team should handle this message?",
        criteria={
            "billing": "Payments, invoices, refunds",
            "technical": "Bugs, outages, integrations",
            "sales": "Pricing, upgrades, new accounts",
        },
    ),
}

try:
    # 3. CLIENT: reads the key, defaults to model "jev-latest", retries 429/5xx for us.
    with TypeSafeClient(**client_kwargs(offline)) as client:
        response = client.system_one(state=state, questions=questions)
except TypeSafeAuthenticationError:
    raise SystemExit("401: the API key was rejected. Check TYPESAFE_API_KEY in .env.") from None
except TypeSafeRateLimitError as err:
    raise SystemExit(
        f"429: still rate limited after retries (retry after {err.retry_after_ms} ms)"
    ) from None
except TypeSafeAPIError as err:
    raise SystemExit(f"API error {err.status} (request id {err.request_id})") from None
except TypeSafeAPIConnectionError:
    raise SystemExit("Could not reach api.typesafe.ai (network, proxy or timeout).") from None
except TypeSafeError as err:  # e.g. no key configured at all
    raise SystemExit(f"Client setup failed: {err}") from None

# 4. TYPED ANSWERS: no string parsing anywhere.
department = response.choices["department"]
urgency = response.nouls["is_urgent"]

print(f"model that answered : {response.model}")
print(f"department          : {department.choice}  (confidence {department.confidence:.2f})")
print(f"probabilities       : {department.probabilities}")
print(f"P(urgent)           : {urgency.noul:.2f}")
print(f"input tokens        : {response.usage.input_tokens}")

# 5. The raw JSON, so you can see exactly what came over the wire.
print("\nraw response body:")
print(json.dumps(response.raw_http_response.json(), indent=2))

# Our code can now branch on a value, like any other function result:
if department.choice == "billing":
    print("\n-> would go to the billing queue")
