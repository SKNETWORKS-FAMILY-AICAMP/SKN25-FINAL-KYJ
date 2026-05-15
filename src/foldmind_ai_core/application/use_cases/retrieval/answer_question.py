from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.agents.answer_generator_agent import AnswerGeneratorAgent
from foldmind_ai_core.application.services.use_case_contracts import DocumentFinder
from foldmind_ai_core.domain.generation.results import GeneratedTextResult
from foldmind_ai_core.domain.retrieval.queries import AIQuery


@dataclass(slots=True)
class AnswerQuestionUseCase:
    find_documents: DocumentFinder
    answer_generator: AnswerGeneratorAgent

    def execute(self, query: AIQuery) -> GeneratedTextResult:
        results = self.find_documents.execute(query)
        return self.answer_generator.answer(query=query, citations=results)
