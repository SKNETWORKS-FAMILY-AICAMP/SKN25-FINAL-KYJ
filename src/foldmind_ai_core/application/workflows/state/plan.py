from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WorkflowActionType(StrEnum):
    FIND_DOCUMENTS = "find_documents"
    FIND_FOLDERS = "find_folders"
    FIND_RELATED = "find_related"
    CLASSIFY_DOCUMENTS = "classify_documents"
    ANALYZE_DOCUMENTS = "analyze_documents"
    SYNTHESIZE_REPORT = "synthesize_report"
    RECOMMEND_DOCUMENTS = "recommend_documents"
    RECOMMEND_FOLDER = "recommend_folder"
    RECOMMEND_RELATED = "recommend_related"
    ANSWER_QUESTION = "answer_question"
    SUMMARIZE_DOCUMENTS = "summarize_documents"
    GENERATE_DRAFT = "generate_draft"
    EXPLORE_IDEAS = "explore_ideas"
    PLAN_HOST_ACTIONS = "plan_host_actions"


class WorkflowRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WorkflowAction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    action_type: WorkflowActionType = Field(alias="type")
    reason: str = ""
    params: dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = False

    @field_validator("params")
    @classmethod
    def validate_params(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not _is_json_object(value):
            raise ValueError("params must contain only JSON-compatible values.")
        return value


class WorkflowPlan(BaseModel):
    intent: str = Field(min_length=1)
    topic: str | None = None
    source_scope: str | None = None
    risk_level: WorkflowRiskLevel = WorkflowRiskLevel.LOW
    requires_confirmation: bool = False
    actions: list[WorkflowAction] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_action_dependencies(self) -> WorkflowPlan:
        seen: set[WorkflowActionType] = set()
        for action in self.actions:
            for required in _required_prior_actions(action.action_type):
                if required not in seen:
                    raise ValueError(
                        f"{action.action_type.value} requires {required.value} earlier in the plan."
                    )
            seen.add(action.action_type)
        return self


def _is_json_object(value: dict[str, Any]) -> bool:
    return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())


def _is_json_value(value: object) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return _is_json_object(value)
    return False


def _required_prior_actions(action_type: WorkflowActionType) -> tuple[WorkflowActionType, ...]:
    requirements: dict[WorkflowActionType, tuple[WorkflowActionType, ...]] = {
        WorkflowActionType.RECOMMEND_DOCUMENTS: (WorkflowActionType.FIND_DOCUMENTS,),
        WorkflowActionType.ANSWER_QUESTION: (WorkflowActionType.FIND_DOCUMENTS,),
        WorkflowActionType.SUMMARIZE_DOCUMENTS: (WorkflowActionType.FIND_DOCUMENTS,),
        WorkflowActionType.GENERATE_DRAFT: (WorkflowActionType.FIND_DOCUMENTS,),
        WorkflowActionType.EXPLORE_IDEAS: (WorkflowActionType.FIND_DOCUMENTS,),
        WorkflowActionType.CLASSIFY_DOCUMENTS: (WorkflowActionType.FIND_DOCUMENTS,),
        WorkflowActionType.ANALYZE_DOCUMENTS: (WorkflowActionType.CLASSIFY_DOCUMENTS,),
        WorkflowActionType.SYNTHESIZE_REPORT: (WorkflowActionType.ANALYZE_DOCUMENTS,),
        WorkflowActionType.RECOMMEND_FOLDER: (WorkflowActionType.FIND_FOLDERS,),
    }
    return requirements.get(action_type, ())
