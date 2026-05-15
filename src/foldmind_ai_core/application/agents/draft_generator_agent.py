from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.agents.rag_generation import (
    generate_from_retrieved_context,
)
from foldmind_ai_core.application.ports.outbound.llm import LLM
from foldmind_ai_core.application.ports.outbound.prompt_repository import PromptRepositoryPort
from foldmind_ai_core.application.services.prompts import PROMPT_DRAFT_GENERATION
from foldmind_ai_core.domain.generation.results import DraftResult
from foldmind_ai_core.domain.retrieval.results import RetrievalResult


@dataclass(slots=True)
class DraftGeneratorAgent:
    llm: LLM
    prompt_repository: PromptRepositoryPort

    def generate(self, *, instruction: str, citations: list[RetrievalResult]) -> DraftResult:
        draft = generate_from_retrieved_context(
            llm=self.llm,
            prompt_repository=self.prompt_repository,
            prompt_name=PROMPT_DRAFT_GENERATION,
            citations=citations,
            user_suffix=f"\n\nInstruction:\n{instruction}",
        )
        return DraftResult(draft=draft, citations=citations)
