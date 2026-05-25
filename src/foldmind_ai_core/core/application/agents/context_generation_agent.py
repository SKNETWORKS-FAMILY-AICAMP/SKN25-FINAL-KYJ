from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.formatters.retrieved_context import (
    UNTRUSTED_CONTEXT_INSTRUCTION,
    format_untrusted_context,
)
from foldmind_ai_core.core.application.models.llm import LLMMessage
from foldmind_ai_core.core.application.ports.outbound.provider.llm import LLMProvider
from foldmind_ai_core.core.application.ports.outbound.provider.prompt_store import PromptStore
from foldmind_ai_core.core.application.prompts import (
    TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION,
    render_prompt,
)
from foldmind_ai_core.core.application.models.generation import GeneratedTextResult
from foldmind_ai_core.core.application.models.retrieval import RetrievalResult


@dataclass(slots=True)
class ContextGenerationAgent:
    llm: LLMProvider
    prompt_store: PromptStore

    async def generate(
        self,
        *,
        prompt_name: str,
        instruction: str,
        citations: list[RetrievalResult],
    ) -> GeneratedTextResult:
        context = format_untrusted_context(citations)
        text = await self.llm.generate(
            [
                LLMMessage(
                    role="system",
                    content=render_prompt(
                        self.prompt_store.get(prompt_name),
                        {
                            TOKEN_UNTRUSTED_CONTEXT_INSTRUCTION: (
                                UNTRUSTED_CONTEXT_INSTRUCTION
                            ),
                        },
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"Retrieved context JSON:\n{context}"
                        f"\n\nInstruction:\n{instruction}"
                    ),
                ),
            ]
        )
        return GeneratedTextResult(text=text, citations=citations)
