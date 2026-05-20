from __future__ import annotations
from dataclasses import dataclass

from foldmind_ai_core.core.domain.services.confidence import require_confidence_value


@dataclass(frozen=True, slots=True)
class Confidence:
    value: float

    def __post_init__(self) -> None:
        confidence = require_confidence_value(self.value)
        object.__setattr__(self, "value", confidence)
