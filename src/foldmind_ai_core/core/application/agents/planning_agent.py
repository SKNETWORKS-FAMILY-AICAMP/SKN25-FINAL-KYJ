from __future__ import annotations

import json
from dataclasses import dataclass

from foldmind_ai_core.core.application.agents.json_output import parse_json_object_output
from foldmind_ai_core.core.application.models.llm import LLMMessage
from foldmind_ai_core.core.application.ports.outbound.llm import LLMProvider
from foldmind_ai_core.core.application.ports.outbound.prompt_store import PromptStore
from foldmind_ai_core.core.application.services.prompts import (
    PROMPT_WORKFLOW_PLANNING,
    TOKEN_ALLOWED_WORKFLOW_ACTION_TYPES,
    render_prompt,
)
from foldmind_ai_core.core.application.workflows.state.plan import (
    WorkflowActionType,
    WorkflowPlan,
)
from foldmind_ai_core.core.application.workflows.plan_factory import (
    workflow_plan_from_mapping,
)
from foldmind_ai_core.core.application.queries.retrieval import RetrievalQuery


class PlanningError(RuntimeError):
    """Raised when the planner returns an invalid workflow plan."""


@dataclass(slots=True)
class PlanningAgent:
    prompt_store: PromptStore
    llm: LLMProvider

    def plan(self, query: RetrievalQuery) -> WorkflowPlan:
        payload = {
            "request": query.text,
            "request_context": {
                "tenant": query.request_context.tenant,
                "requested_at": query.request_context.requested_at,
                "document_id": query.request_context.document_id,
                "folder_id": query.request_context.folder_id,
                "metadata": query.request_context.metadata,
            },
        }
        system_prompt = render_prompt(
            self.prompt_store.get(PROMPT_WORKFLOW_PLANNING),
            {
                TOKEN_ALLOWED_WORKFLOW_ACTION_TYPES: ", ".join(
                    action.value for action in WorkflowActionType
                ),
            },
        )
        response = self.llm.generate(
            [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=json.dumps(payload, ensure_ascii=False)),
            ]
        )
        try:
            return workflow_plan_from_mapping(parse_json_object_output(response))
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            raise PlanningError("Planner failed to produce a valid workflow plan.") from exc
