"""Application configuration, loaded from environment variables (and an optional .env file).

Every threshold in this file is an APPLICATION POLICY chosen by this project.
None of them is a TypeSafe/Jev recommendation. TypeSafe's docs say the right values
"depend on your domain" and should be tuned on your own data - see evaluation/evaluate.py.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Jev / TypeSafe -------------------------------------------------------------
    # "typesafe" calls the real API. "mock" uses an OFFLINE keyword mock (see
    # app/services/mock_backend.py) whose output is NOT model output.
    jev_backend: Literal["typesafe", "mock"] = "typesafe"
    # Read by our code and passed explicitly to the SDK. SecretStr keeps it out of reprs/logs.
    typesafe_api_key: SecretStr | None = None
    # Pin a version (e.g. "jev-1.13.0") once your thresholds are tuned; aliases can move.
    jev_model: str = "jev-latest"
    jev_timeout_seconds: float = Field(default=5.0, gt=0)  # per HTTP attempt
    jev_max_retries: int = Field(default=2, ge=0, le=5)  # SDK retries (429/5xx/timeouts)
    jev_retry_budget_seconds: float = Field(default=10.0, gt=0)  # total time incl. backoff

    # --- Automation policy (application-level, tune with evaluation data) -----------
    auto_route_min_confidence: float = Field(default=0.60, ge=0, le=1)
    min_top2_margin: float = Field(default=0.15, ge=0, le=1)
    priority_min_confidence: float = Field(default=0.40, ge=0, le=1)
    human_review_noul_threshold: float = Field(default=0.50, ge=0, le=1)
    # Escalate if the probability of "critical" alone reaches this, even if it isn't the argmax.
    critical_escalation_probability: float = Field(default=0.25, ge=0, le=1)
    # Priorities that ALWAYS go to a human, no matter how confident the model is.
    # Accepts "critical", "critical,high" or the JSON form ["critical"] in .env.
    mandatory_review_priorities: Annotated[list[str], NoDecode] = ["critical"]

    # --- Input limits & privacy ---------------------------------------------------
    max_message_chars: int = Field(default=4000, gt=0)
    redact_pii: bool = True

    # --- Infrastructure -----------------------------------------------------------
    database_url: str = "sqlite:///./tickets.db"
    log_level: str = "INFO"

    @field_validator("mandatory_review_priorities", mode="before")
    @classmethod
    def _parse_priority_list(cls, value):
        if isinstance(value, str):
            # Straighten "smart" quotes that editors and websites insert automatically.
            text = value.strip().translate(str.maketrans("\u201c\u201d\u2018\u2019", "\"\"''"))
            if text.startswith("["):
                import json

                return json.loads(text)
            return [part.strip().strip("\"'") for part in text.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
