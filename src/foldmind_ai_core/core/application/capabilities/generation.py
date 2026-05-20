from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.queries.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.workflows.state.plan import WorkflowPlan
from foldmind_ai_core.core.domain.models.generation.results import GeneratedTextResult
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievalResult


class ContextGenerationCapability(Protocol):
    def generate(
        self,
        *,
        prompt_name: str,
        instruction: str,
        citations: list[RetrievalResult],
    ) -> GeneratedTextResult:
        ...


class WorkflowPlanningCapability(Protocol):
    def plan(self, query: RetrievalQuery) -> WorkflowPlan:
        ...
