from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpenAISettings:
    api_key: str
    base_url: str | None = None
    timeout_seconds: float = 60.0
    max_retries: int = 2
