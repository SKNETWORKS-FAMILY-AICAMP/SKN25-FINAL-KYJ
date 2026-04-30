from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class APIBaseDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


def to_plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, list | tuple):
        return [to_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain(item) for key, item in value.items()}
    return value
