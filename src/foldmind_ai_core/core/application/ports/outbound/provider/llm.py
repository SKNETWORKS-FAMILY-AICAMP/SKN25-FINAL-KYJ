from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.models.llm import LLMMessage


class LLMProvider(Protocol):
    async def generate(self, messages: list[LLMMessage]) -> str:
        """Generate a text response from chat-style messages."""
        ...
