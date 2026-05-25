from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.domain.models.confidence import Confidence
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(frozen=True, slots=True)
class ConfidenceService:
    def normalize(self, confidence: Confidence | float | None) -> float | None:
        if confidence is None:
            return None
        if isinstance(confidence, Confidence):
            return confidence.value
        return Confidence(confidence).value

    def require(self, confidence: Confidence | float) -> float:
        score = self.normalize(confidence)
        if score is None:
            raise InvalidInputError("confidence must be numeric.")
        return score
