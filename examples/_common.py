"""Tiny helper shared by the examples: choose real API vs. the offline mock.

Real API (default):   python examples/01_first_request.py
Offline mock:         python examples/01_first_request.py --offline
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable

from app.config import Settings  # noqa: E402
from app.services.mock_backend import MOCK_API_KEY, mock_transport  # noqa: E402

OFFLINE_BANNER = (
    "*** OFFLINE MOCK: answers below come from a keyword heuristic, NOT from Jev. ***\n"
)


def parse_offline_flag(description: str) -> bool:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--offline", action="store_true", help="use the offline mock, not Jev")
    offline = parser.parse_args().offline
    if offline:
        print(OFFLINE_BANNER)
    return offline


def client_kwargs(offline: bool) -> dict:
    """Extra keyword arguments for TypeSafeClient / AsyncTypeSafeClient.

    Online: the key from .env (if set). Otherwise {} and the SDK falls back to the
            TYPESAFE_API_KEY environment variable, raising TypeSafeError if neither exists.
    Offline: a fake key plus a mock HTTP transport; the real SDK still parses everything.
    """
    if offline:
        return {"api_key": MOCK_API_KEY, "transport": mock_transport()}
    key = Settings().typesafe_api_key
    return {"api_key": key.get_secret_value()} if key else {}
