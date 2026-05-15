from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.openai.client import (
    OpenAIClient,
    field_value,
)
from foldmind_ai_core.adapters.outbound.openai.errors import AIProviderError
from foldmind_ai_core.application.dto.llm import LLMMessage
from foldmind_ai_core.shared.validation import InvalidInputError, require_non_blank


@dataclass(slots=True)
class OpenAILLM:
    model: str
    client: OpenAIClient

    def __post_init__(self) -> None:
        require_non_blank(self.model, "model")

    def generate(self, messages: list[LLMMessage]) -> str:
        if not messages:
            raise InvalidInputError("messages must not be empty.")
        try:
            response = self.client.create_response(
                model=self.model,
                input=[
                    {
                        "role": message.role,
                        "content": message.content,
                    }
                    for message in messages
                ],
            )
        except Exception as exc:
            raise AIProviderError("OpenAI response generation failed.") from exc

        text = field_value(response, "output_text")
        if not isinstance(text, str) or not text.strip():
            raise AIProviderError("OpenAI response did not include non-empty output_text.")
        return text
