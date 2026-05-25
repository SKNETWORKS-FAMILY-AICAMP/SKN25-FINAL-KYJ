from __future__ import annotations

from typing import Protocol


class PromptStore(Protocol):
    def get(self, name: str) -> str:
        ...
