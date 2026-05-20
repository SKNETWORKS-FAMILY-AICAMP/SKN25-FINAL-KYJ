from __future__ import annotations

import math
from typing import TYPE_CHECKING

from foldmind_ai_core.shared.validation import InvalidInputError

if TYPE_CHECKING:
    from foldmind_ai_core.core.domain.models.confidence import Confidence


def normalize_confidence_value(confidence: Confidence | float | None) -> float | None:
    if confidence is None:
        return None
    value = getattr(confidence, "value", confidence)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InvalidInputError("confidence must be numeric.")
    score = float(value)
    if not math.isfinite(score) or score < 0.0 or score > 1.0:
        raise InvalidInputError("confidence must be between 0 and 1.")
    return score


def require_confidence_value(confidence: Confidence | float) -> float:
    score = normalize_confidence_value(confidence)
    if score is None:
        raise InvalidInputError("confidence must be numeric.")
    return score
