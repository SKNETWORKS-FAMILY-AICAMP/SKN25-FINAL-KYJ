from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.agents.rag_generation import (
    generate_from_retrieved_context,
)
from foldmind_ai_core.application.ports.outbound.llm import LLM
from foldmind_ai_core.application.ports.outbound.prompt_repository import PromptRepositoryPort
from foldmind_ai_core.application.services.prompts import PROMPT_IDEAS_EXPLORATION
from foldmind_ai_core.domain.generation.results import GeneratedTextResult
from foldmind_ai_core.domain.retrieval.results import RetrievalResult


@dataclass(slots=True)
class IdeasExplorerAgent:
    llm: LLM
    prompt_repository: PromptRepositoryPort

    def explore(self, *, prompt: str, citations: list[RetrievalResult]) -> GeneratedTextResult:
        text = generate_from_retrieved_context(
            llm=self.llm,
            prompt_repository=self.prompt_repository,
            prompt_name=PROMPT_IDEAS_EXPLORATION,
            citations=citations,
            user_suffix=f"\n\nPrompt:\n{prompt}",
        )
        return GeneratedTextResult(text=text, citations=citations)
