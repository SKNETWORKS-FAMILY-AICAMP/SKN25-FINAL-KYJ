from __future__ import annotations

import math
from collections.abc import Mapping

from foldmind_ai_core.shared.types import JsonObject


def json_object_value(value: object, name: str) -> JsonObject:
    if not isinstance(value, dict) or not _is_json_object(value):
        raise ValueError(f"{name} must contain only JSON-compatible values.")
    return dict(value)


def _is_json_object(value: Mapping[object, object]) -> bool:
    return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())


def _is_json_value(value: object) -> bool:
    if value is None or isinstance(value, str | int | bool):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return _is_json_object(value)
    return False
