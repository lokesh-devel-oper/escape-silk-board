from __future__ import annotations

import os
from dataclasses import dataclass


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


def _bounded_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class AISettings:
    api_key: str | None
    model: str | None
    timeout_seconds: float = 5.0
    max_retries: int = 1
    minimum_confidence: float = 0.55

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    @classmethod
    def from_env(cls) -> "AISettings":
        api_key = os.getenv("GEMINI_API_KEY", "").strip() or None
        model = os.getenv("GEMINI_MODEL", "").strip() or None
        return cls(
            api_key=api_key,
            model=model,
            timeout_seconds=_bounded_float("GEMINI_TIMEOUT_SECONDS", 5.0, 0.5, 30.0),
            max_retries=_bounded_int("GEMINI_MAX_RETRIES", 1, 0, 2),
            minimum_confidence=_bounded_float("GEMINI_MIN_CONFIDENCE", 0.55, 0.0, 1.0),
        )

