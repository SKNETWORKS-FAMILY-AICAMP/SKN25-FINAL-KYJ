from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

from foldmind_ai_core.core.application.workflows.state.json_values import json_object_value
from foldmind_ai_core.core.application.workflows.state.plan import (
    WorkflowAction,
    WorkflowActionType,
    WorkflowParams,
    WorkflowPlan,
    WorkflowRiskLevel,
)

_E = TypeVar("_E", WorkflowActionType, WorkflowRiskLevel)


def workflow_plan_from_mapping(payload: Mapping[str, object]) -> WorkflowPlan:
    unknown = set(payload) - {
        "intent",
        "topic",
        "source_scope",
        "risk_level",
        "requires_confirmation",
        "actions",
    }
    if unknown:
        raise ValueError(f"Workflow plan contains unsupported fields: {sorted(unknown)}")

    raw_actions = _required_value(payload, "actions")
    if not isinstance(raw_actions, list) or not raw_actions:
        raise ValueError("actions must contain at least one workflow action.")
    return WorkflowPlan(
        intent=_string_value(_required_value(payload, "intent"), "intent"),
        topic=_optional_string(payload.get("topic"), "topic"),
        source_scope=_optional_string(payload.get("source_scope"), "source_scope"),
        risk_level=_enum_value(
            WorkflowRiskLevel,
            payload.get("risk_level", WorkflowRiskLevel.LOW),
            "risk_level",
        ),
        requires_confirmation=_bool_value(
            payload.get("requires_confirmation", False),
            "requires_confirmation",
        ),
        actions=[workflow_action_from_mapping(item) for item in raw_actions],
    )


def workflow_action_from_mapping(payload: object) -> WorkflowAction:
    if not isinstance(payload, Mapping):
        raise ValueError("workflow action must be a JSON object.")

    unknown = set(payload) - {"type", "reason", "params", "requires_confirmation"}
    if unknown:
        raise ValueError(f"Workflow action contains unsupported fields: {sorted(unknown)}")

    return WorkflowAction(
        action_type=_enum_value(
            WorkflowActionType,
            _required_value(payload, "type"),
            "type",
        ),
        reason=_optional_string(payload.get("reason"), "reason", default="") or "",
        params=_params_value(payload.get("params", {})),
        requires_confirmation=_bool_value(
            payload.get("requires_confirmation", False),
            "requires_confirmation",
        ),
    )


def _required_value(payload: Mapping[str, object], key: str) -> object:
    if key not in payload:
        raise ValueError(f"{key} is required.")
    return payload[key]


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


def _params_value(value: object) -> WorkflowParams:
    return json_object_value(value, "params")


def _bool_value(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean.")
    return value
