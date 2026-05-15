from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from foldmind_ai_core.adapters.outbound.openai.settings import OpenAISettings
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(slots=True)
class OpenAIClient:
    settings: OpenAISettings
    sdk_client: Any | None = None
    _sdk_client: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._sdk_client = self.sdk_client or _new_openai_client(self.settings)

    def create_response(
        self,
        *,
        model: str,
        input: list[dict[str, str]],
    ) -> Any:
        return self._sdk_client.responses.create(model=model, input=input)

    def create_embeddings(self, request: dict[str, object]) -> Any:
        return self._sdk_client.embeddings.create(**request)


def field_value(value: object, name: str) -> Any:
    if isinstance(value, dict):
        return value[name]
    return getattr(value, name)


def _new_openai_client(settings: OpenAISettings) -> Any:
    if not settings.api_key:
        raise InvalidInputError("OPENAI_API_KEY is required when AI_PROVIDER=openai.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai package is required when AI_PROVIDER=openai.") from exc

    kwargs: dict[str, object] = {
        "api_key": settings.api_key,
        "timeout": settings.timeout_seconds,
        "max_retries": settings.max_retries,
    }
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
    return OpenAI(**kwargs)
