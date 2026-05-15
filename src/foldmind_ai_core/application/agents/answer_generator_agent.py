from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.agents.rag_generation import (
    generate_from_retrieved_context,
)
from foldmind_ai_core.application.ports.outbound.llm import LLM
from foldmind_ai_core.application.ports.outbound.prompt_repository import PromptRepositoryPort
from foldmind_ai_core.application.services.prompts import PROMPT_ANSWER_GENERATION
from foldmind_ai_core.domain.generation.results import GeneratedTextResult
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.retrieval.results import RetrievalResult


@dataclass(slots=True)
class AnswerGeneratorAgent:
    llm: LLM
    prompt_repository: PromptRepositoryPort

    def answer(self, *, query: AIQuery, citations: list[RetrievalResult]) -> GeneratedTextResult:
        answer = generate_from_retrieved_context(
            llm=self.llm,
            prompt_repository=self.prompt_repository,
            prompt_name=PROMPT_ANSWER_GENERATION,
            citations=citations,
            user_suffix=f"\n\nQuestion:\n{query.text}",
        )
        return GeneratedTextResult(text=answer, citations=citations)
