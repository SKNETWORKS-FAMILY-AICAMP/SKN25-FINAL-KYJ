from __future__ import annotations

from dataclasses import dataclass

from ai_core.domain.tasks import AssistantExecutionPlan, AssistantToolCall, AssistantToolName, AIQuery


@dataclass(slots=True)
class WorkflowPlanner:
    def plan(self, query: AIQuery) -> AssistantExecutionPlan:
        return AssistantExecutionPlan(
            steps=[
                AssistantToolCall(
                    tool_name=AssistantToolName.SEARCH_DOCUMENTS,
                    reason="Find relevant indexed document chunks.",
                ),
                AssistantToolCall(
                    tool_name=AssistantToolName.ANSWER_QUESTION,
                    reason="Generate a response grounded in retrieved context.",
                ),
            ]
        )
