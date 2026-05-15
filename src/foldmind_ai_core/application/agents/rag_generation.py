from __future__ import annotations

from foldmind_ai_core.application.dto.llm import LLMMessage
from foldmind_ai_core.application.ports.outbound.llm import LLM
from foldmind_ai_core.application.ports.outbound.prompt_repository import PromptRepositoryPort
from foldmind_ai_core.application.services.prompts import (
    TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION,
    render_prompt,
)
from foldmind_ai_core.application.services.rag_context import (
    UNTRUSTED_CONTEXT_INSTRUCTION,
    format_untrusted_context,
)
from foldmind_ai_core.domain.retrieval.results import RetrievalResult


def generate_from_retrieved_context(
    *,
    llm: LLM,
    prompt_repository: PromptRepositoryPort,
    prompt_name: str,
    citations: list[RetrievalResult],
    user_suffix: str = "",
) -> str:
    context = format_untrusted_context(citations)
    return llm.generate(
        [
            LLMMessage(
                role="system",
                content=render_prompt(
                    prompt_repository.get(prompt_name),
                    {
                        TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION: (
                            UNTRUSTED_CONTEXT_INSTRUCTION
                        ),
                    },
                ),
            ),
            LLMMessage(
                role="user",
                content=f"Retrieved context JSON:\n{context}{user_suffix}",
            ),
        ]
    )
