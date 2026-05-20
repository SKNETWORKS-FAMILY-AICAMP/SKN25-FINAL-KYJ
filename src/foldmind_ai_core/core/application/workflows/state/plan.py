from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeVar

from foldmind_ai_core.core.application.workflows.state.json_values import json_object_value
from foldmind_ai_core.shared.types import JsonObject

WorkflowParams = JsonObject


class WorkflowActionType(StrEnum):
    FIND_DOCUMENTS = "find_documents"
    PRESENT_DOCUMENTS = "present_documents"
    FIND_SIGNALS = "find_signals"
    PRESENT_SIGNALS = "present_signals"
    EXPAND_SIGNAL_EVIDENCE = "expand_signal_evidence"
    SYNTHESIZE_SIGNALS = "synthesize_signals"
    EXTRACT_ON_DEMAND_SIGNALS = "extract_on_demand_signals"
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
    REQUEST_CLARIFICATION = "request_clarification"


class WorkflowRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


_E = TypeVar("_E", WorkflowActionType, WorkflowRiskLevel)


_REQUIRED_PRIOR_ACTIONS: dict[WorkflowActionType, tuple[WorkflowActionType, ...]] = {
    WorkflowActionType.PRESENT_DOCUMENTS: (WorkflowActionType.FIND_DOCUMENTS,),
    WorkflowActionType.PRESENT_SIGNALS: (WorkflowActionType.FIND_SIGNALS,),
    WorkflowActionType.EXPAND_SIGNAL_EVIDENCE: (WorkflowActionType.FIND_SIGNALS,),
    WorkflowActionType.SYNTHESIZE_SIGNALS: (WorkflowActionType.FIND_SIGNALS,),
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

_ACTION_TYPES_REQUIRING_INSTRUCTION = {
    WorkflowActionType.ANSWER_QUESTION,
    WorkflowActionType.SUMMARIZE_DOCUMENTS,
    WorkflowActionType.GENERATE_DRAFT,
    WorkflowActionType.EXPLORE_IDEAS,
    WorkflowActionType.ANALYZE_DOCUMENTS,
    WorkflowActionType.SYNTHESIZE_SIGNALS,
}


@dataclass(slots=True)
class WorkflowAction:
    action_type: WorkflowActionType
    reason: str = ""
    params: WorkflowParams = field(default_factory=dict)
    requires_confirmation: bool = False

    def __post_init__(self) -> None:
        self.action_type = _enum_value(
            WorkflowActionType,
            self.action_type,
            "action_type",
        )
        self.reason = _optional_string(self.reason, "reason", default="")
        self.requires_confirmation = _bool_value(
            self.requires_confirmation,
            "requires_confirmation",
        )
        self.params = _params_value(self.params)


@dataclass(slots=True)
class WorkflowPlan:
    intent: str
    actions: list[WorkflowAction]
    topic: str | None = None
    source_scope: str | None = None
    risk_level: WorkflowRiskLevel = WorkflowRiskLevel.LOW
    requires_confirmation: bool = False

    def __post_init__(self) -> None:
        self.intent = _string_value(self.intent, "intent")
        self.topic = _optional_string(self.topic, "topic")
        self.source_scope = _optional_string(self.source_scope, "source_scope")
        self.risk_level = _enum_value(WorkflowRiskLevel, self.risk_level, "risk_level")
        self.requires_confirmation = _bool_value(
            self.requires_confirmation,
            "requires_confirmation",
        )
        if not self.actions:
            raise ValueError("actions must contain at least one workflow action.")
        self.actions = [_workflow_action_value(action) for action in self.actions]
        self._validate_action_params()
        self._validate_action_dependencies()

    def _validate_action_params(self) -> None:
        for action in self.actions:
            if action.action_type in _ACTION_TYPES_REQUIRING_INSTRUCTION:
                if "instruction" not in action.params:
                    raise ValueError(
                        f"{action.action_type.value}.params.instruction must be a non-blank string."
                    )
                action.params["instruction"] = _instruction_param_value(
                    action.params["instruction"],
                    f"{action.action_type.value}.params.instruction",
                )

    def _validate_action_dependencies(self) -> None:
        seen: set[WorkflowActionType] = set()
        for action in self.actions:
            for required in _REQUIRED_PRIOR_ACTIONS.get(action.action_type, ()):
                if required not in seen:
                    raise ValueError(
                        f"{action.action_type.value} requires {required.value} earlier in the plan."
                    )
            seen.add(action.action_type)


def _string_value(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be blank.")
    return normalized


def _optional_string(value: object, name: str, *, default: str | None = None) -> str | None:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string.")
    return value.strip() if default is None else value


def _enum_value(enum_type: type[_E], value: object, name: str) -> _E:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        return enum_type(value.strip())
    raise ValueError(f"{name} must be a string.")


def _workflow_action_value(value: object) -> WorkflowAction:
    if isinstance(value, WorkflowAction):
        return value
    raise ValueError("actions must contain workflow actions.")


def _params_value(value: object) -> WorkflowParams:
    return json_object_value(value, "params")


def _bool_value(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean.")
    return value


def _instruction_param_value(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a non-blank string.")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be a non-blank string.")
    return normalized

