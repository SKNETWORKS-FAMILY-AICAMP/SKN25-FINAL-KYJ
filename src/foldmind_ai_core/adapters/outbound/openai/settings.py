from __future__ import annotations

import math
from dataclasses import dataclass

from foldmind_ai_core.shared.validation import InvalidInputError, require_non_blank


@dataclass(frozen=True, slots=True)
class OpenAISettings:
    api_key: str
    base_url: str | None = None
    timeout_seconds: float = 60.0
    max_retries: int = 2

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "api_key",
            require_non_blank(self.api_key, "api_key"),
        )
        if self.base_url is not None:
            object.__setattr__(
                self,
                "base_url",
                require_non_blank(self.base_url, "base_url"),
            )
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, int | float)
            or not math.isfinite(float(self.timeout_seconds))
            or self.timeout_seconds <= 0
        ):
            raise InvalidInputError("timeout_seconds must be a positive finite number.")
        if (
            isinstance(self.max_retries, bool)
            or not isinstance(self.max_retries, int)
            or self.max_retries < 0
        ):
            raise InvalidInputError("max_retries must be a non-negative integer.")
