from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any

from foldmind_ai_core.adapters.outbound.openai.settings import OpenAISettings


@dataclass(slots=True)
class OpenAIClient:
    settings: OpenAISettings
    sdk_client: Any | None = None
    _embedding_client: Any = field(init=False, repr=False)
    _response_client: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.sdk_client is not None:
            self._embedding_client = self.sdk_client
            self._response_client = self.sdk_client
            return
        try:
            from openai import AsyncOpenAI, OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The openai package is required when FOLDMIND_AI_PROVIDER=openai."
            ) from exc

        kwargs: dict[str, object] = {
            "api_key": self.settings.api_key,
            "timeout": self.settings.timeout_seconds,
            "max_retries": self.settings.max_retries,
        }
        if self.settings.base_url:
            kwargs["base_url"] = self.settings.base_url
        self._embedding_client = OpenAI(**kwargs)
        self._response_client = AsyncOpenAI(**kwargs)

    async def create_response(
        self,
        *,
        model: str,
        input: list[dict[str, str]],
    ) -> Any:
        response = self._response_client.responses.create(model=model, input=input)
        if inspect.isawaitable(response):
            return await response
        return response

    def create_embeddings(self, request: dict[str, object]) -> Any:
        return self._embedding_client.embeddings.create(**request)


def field_value(value: object, name: str) -> Any:
    if isinstance(value, dict):
        return value[name]
    return getattr(value, name)
