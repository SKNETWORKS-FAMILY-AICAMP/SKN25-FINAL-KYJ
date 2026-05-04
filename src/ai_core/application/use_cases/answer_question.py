from __future__ import annotations

from dataclasses import dataclass

from ai_core.agents.answer_generator import AnswerGeneratorAgent
from ai_core.agents.search_agent import SearchAgent
from ai_core.application.models.queries import AIQuery
from ai_core.application.models.results import GeneratedTextResult


@dataclass(slots=True)
class AnswerQuestionUseCase:
    search: SearchAgent
    answer_generator: AnswerGeneratorAgent

    def execute(self, query: AIQuery) -> GeneratedTextResult:
        results = self.search.search_documents(query)
        return self.answer_generator.answer(query=query, citations=results)
