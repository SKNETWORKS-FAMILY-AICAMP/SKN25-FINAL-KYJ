from __future__ import annotations

from typing import Protocol

from ai_core.schemas.llm import LLMMessage


class LLM(Protocol):
    def generate(self, messages: list[LLMMessage]) -> str:
        """Generate a text response from chat-style messages."""
