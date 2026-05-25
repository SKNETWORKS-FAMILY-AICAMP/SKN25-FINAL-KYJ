from __future__ import annotations

from pathlib import Path

from foldmind_ai_core.bootstrap.container.dependencies import AIProviders
from foldmind_ai_core.bootstrap.settings import AIProvider, APISettings
from foldmind_ai_core.core.application.ports.outbound.provider.prompt_store import PromptStore


def _build_ai_providers(settings: APISettings) -> AIProviders:
    try:
        provider = AIProvider(settings.ai_provider)
    except ValueError as exc:
        raise RuntimeError(
            f"Unsupported FOLDMIND_AI_PROVIDER: {settings.ai_provider}"
        ) from exc

    if provider is AIProvider.OPENAI:
        from foldmind_ai_core.adapters.outbound.openai.client import OpenAIClient
        from foldmind_ai_core.adapters.outbound.openai.embeddings import (
            OpenAIEmbeddingProvider,
        )
        from foldmind_ai_core.adapters.outbound.openai.llm import OpenAILLMProvider
        from foldmind_ai_core.adapters.outbound.openai.settings import (
            OpenAISettings,
        )

        client = OpenAIClient(
            settings=OpenAISettings(
                api_key=settings.required_openai_api_key,
                base_url=settings.openai_base_url,
                timeout_seconds=settings.openai_timeout_seconds,
                max_retries=settings.openai_max_retries,
            )
        )
        return AIProviders(
            llm=OpenAILLMProvider(model=settings.llm_model, client=client),
            embeddings=OpenAIEmbeddingProvider(
                model=settings.required_embedding_model,
                dimensions=settings.embedding_dimensions,
                client=client,
            ),
        )
    raise RuntimeError(f"Unsupported FOLDMIND_AI_PROVIDER: {settings.ai_provider}")


def _build_prompt_store(settings: APISettings) -> PromptStore:
    from foldmind_ai_core.adapters.outbound.prompt_store.file_prompt_store import (
        FilePromptStore,
    )

    prompt_root = settings.prompt_root.strip() if settings.prompt_root else None
    root = Path(prompt_root) if prompt_root else default_prompt_root()
    if not root.is_dir():
        raise RuntimeError(f"Prompt root does not exist: {root}")
    return FilePromptStore(root=root)


def default_prompt_root() -> Path:
    return Path(__file__).resolve().parents[2] / "resources" / "prompts"
