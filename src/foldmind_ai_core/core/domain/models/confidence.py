from __future__ import annotations

import math
from dataclasses import dataclass

from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(frozen=True, slots=True)
class Confidence:
    value: float

    def __post_init__(self) -> None:
        confidence = self._normalize(self.value)
        object.__setattr__(self, "value", confidence)

    @staticmethod
    def _normalize(value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise InvalidInputError("confidence must be numeric.")
        score = float(value)
        if not math.isfinite(score) or score < 0.0 or score > 1.0:
            raise InvalidInputError("confidence must be between 0 and 1.")
        return score
