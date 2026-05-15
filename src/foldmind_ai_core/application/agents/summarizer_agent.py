from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.agents.rag_generation import (
    generate_from_retrieved_context,
)
from foldmind_ai_core.application.ports.outbound.llm import LLM
from foldmind_ai_core.application.ports.outbound.prompt_repository import PromptRepositoryPort
from foldmind_ai_core.application.services.prompts import PROMPT_SUMMARIZATION
from foldmind_ai_core.domain.generation.results import GeneratedTextResult
from foldmind_ai_core.domain.retrieval.results import RetrievalResult


@dataclass(slots=True)
class SummarizerAgent:
    llm: LLM
    prompt_repository: PromptRepositoryPort

    def summarize(self, results: list[RetrievalResult]) -> GeneratedTextResult:
        text = generate_from_retrieved_context(
            llm=self.llm,
            prompt_repository=self.prompt_repository,
            prompt_name=PROMPT_SUMMARIZATION,
            citations=results,
        )
        return GeneratedTextResult(text=text, citations=results)
