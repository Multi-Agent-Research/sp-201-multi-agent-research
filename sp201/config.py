"""Settings read from the environment (README, Setup).

Values come from a .env file in the repo root (copy .env.example) or from the
shell. The model ID is never written at a call site (req. 3.11.1).
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_MODEL_ID = "gemini-2.5-flash"


class ConfigError(RuntimeError):
    """A required setting is missing or out of range."""


@dataclass(frozen=True)
class Settings:
    model_id: str
    max_sub_questions: int  # req. 3.1.6: default 3, ceiling 5
    max_revisions: int  # req. 3.6.2: default 1


def _int_setting(name: str, default: int, low: int, high: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a whole number, got {raw!r}.") from None
    if not low <= value <= high:
        raise ConfigError(f"{name} must be between {low} and {high}, got {value}.")
    return value


def load_settings() -> Settings:
    load_dotenv()
    if not os.environ.get("GOOGLE_API_KEY"):
        raise ConfigError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and put your "
            "Google AI Studio key after GOOGLE_API_KEY= (README, Setup)."
        )
    return Settings(
        model_id=os.environ.get("SP201_MODEL_ID") or DEFAULT_MODEL_ID,
        max_sub_questions=_int_setting("SP201_MAX_SUB_QUESTIONS", 3, 1, 5),
        max_revisions=_int_setting("SP201_MAX_REVISIONS", 1, 0, 3),
    )
