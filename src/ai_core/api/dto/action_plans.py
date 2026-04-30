from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from ai_core.api.dto._action_mappings import (
    expected_input_dto_type,
    host_action_input_from_model,
    host_action_type,
)
from ai_core.api.dto.action_inputs import HostActionInputDTO
from ai_core.api.dto.base import APIBaseDTO
from ai_core.application.models.actions import (
    ActionPlan,
    HostAction,
    HostActionPolicy,
    HostActionStatus,
    HostActionType,
)


class HostActionPolicyDTO(APIBaseDTO):
    max_attempts: int = 1
    allow_skip: bool = False
    retryable: bool = False
    requires_confirmation: bool = True

    @classmethod
    def from_model(cls, policy: HostActionPolicy) -> HostActionPolicyDTO:
        return cls(
            max_attempts=policy.max_attempts,
            allow_skip=policy.allow_skip,
            retryable=policy.retryable,
            requires_confirmation=policy.requires_confirmation,
        )


class HostActionDTO(APIBaseDTO):
    action_type: HostActionType
    summary: str
    action_id: str | None = None
    reason: str = ""
    status: HostActionStatus = HostActionStatus.PROPOSED
    input: HostActionInputDTO
    attempts: int = 0
    depends_on: list[str] = Field(default_factory=list)
    policy: HostActionPolicyDTO = Field(default_factory=HostActionPolicyDTO)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_input_matches_action_type(self) -> HostActionDTO:
        expected_input_type = expected_input_dto_type(self.action_type)
        if not isinstance(self.input, expected_input_type):
            raise ValueError(
                f"{self.action_type} action requires {expected_input_type.__name__}."
            )
        return self

    @classmethod
    def from_model(cls, action: HostAction) -> HostActionDTO:
        return cls(
            action_type=host_action_type(action.action_type),
            summary=action.summary,
            action_id=action.action_id,
            reason=action.reason,
            status=action.status,
            input=host_action_input_from_model(action.input),
            attempts=action.attempts,
            depends_on=list(action.depends_on),
            policy=HostActionPolicyDTO.from_model(action.policy),
            metadata=dict(action.metadata),
        )


class ActionPlanDTO(APIBaseDTO):
    summary: str
    steps: list[str] = Field(default_factory=list)
    host_actions: list[HostActionDTO] = Field(default_factory=list)

    @classmethod
    def from_model(cls, plan: ActionPlan) -> ActionPlanDTO:
        return cls(
            summary=plan.summary,
            steps=list(plan.steps),
            host_actions=[HostActionDTO.from_model(action) for action in plan.host_actions],
        )
