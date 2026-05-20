from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any


def transport_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: transport_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, list | tuple):
        return [transport_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): transport_value(item) for key, item in value.items()}
    return value
