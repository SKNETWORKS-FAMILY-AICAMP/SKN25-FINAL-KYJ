from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class LLMMessage:
    role: Literal["system", "user", "assistant"]
    content: str
