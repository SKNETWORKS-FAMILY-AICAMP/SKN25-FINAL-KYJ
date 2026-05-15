from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from foldmind_ai_core.application.dto.llm import LLMMessage
from foldmind_ai_core.application.ports.outbound.llm import LLM
from foldmind_ai_core.application.ports.outbound.prompt_repository import PromptRepositoryPort
from foldmind_ai_core.application.services.prompts import (
    PROMPT_WORKFLOW_PLANNING,
    TOKEN_ALLOWED_WORKFLOW_ACTION_TYPES,
    render_prompt,
)
from foldmind_ai_core.application.workflows.state.plan import (
    WorkflowActionType,
    WorkflowPlan,
)
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.shared.types import Metadata


class PlanningError(RuntimeError):
    pass


@dataclass(slots=True)
class PlanningAgent:
    prompt_repository: PromptRepositoryPort
    llm: LLM

    def plan(self, query: AIQuery) -> WorkflowPlan:
        response = self.llm.generate(
            [
                LLMMessage(role="system", content=self._system_prompt()),
                LLMMessage(role="user", content=self._planning_payload(query)),
            ]
        )
        try:
            return self._plan_from_response(response)
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            raise PlanningError("Planner failed to produce a valid workflow plan.") from exc

    def _planning_payload(self, query: AIQuery) -> str:
        payload: Metadata = {
            "request": query.text,
            "request_context": {
                "tenant": query.request_context.tenant,
                "locale": query.request_context.locale,
                "timezone": query.request_context.timezone,
                "metadata": query.request_context.metadata,
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    def _plan_from_response(self, response: str) -> WorkflowPlan:
        return WorkflowPlan.model_validate(self._json_object(response))

    def _system_prompt(self) -> str:
        return render_prompt(
            self.prompt_repository.get(PROMPT_WORKFLOW_PLANNING),
            {
                TOKEN_ALLOWED_WORKFLOW_ACTION_TYPES: ", ".join(
                    action.value for action in WorkflowActionType
                ),
            },
        )

    def _json_object(self, response: str) -> dict[str, Any]:
        start = response.find("{")
        end = response.rfind("}")
        if start < 0 or end < start:
            raise ValueError("Planner response did not contain a JSON object.")
        payload = json.loads(response[start : end + 1])
        if not isinstance(payload, dict):
            raise ValueError("Planner response JSON must be an object.")
        return payload
