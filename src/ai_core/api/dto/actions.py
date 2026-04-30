from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_core.api.dto._plain import to_plain
from ai_core.application.models.actions import (
    HostAction,
    HostActionPolicy,
    HostActionResult,
    HostActionResultType,
)


class HostActionPolicyDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class HostActionDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: str
    summary: str
    action_id: str | None = None
    reason: str = ""
    status: str = "proposed"
    input: dict[str, Any] | None = None
    attempts: int = 0
    depends_on: list[str] = Field(default_factory=list)
    policy: HostActionPolicyDTO = Field(default_factory=HostActionPolicyDTO)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, action: HostAction) -> HostActionDTO:
        action_input = to_plain(action.input)
        return cls(
            action_type=to_plain(action.action_type),
            summary=action.summary,
            action_id=action.action_id,
            reason=action.reason,
            status=to_plain(action.status),
            input=action_input if isinstance(action_input, dict) else None,
            attempts=action.attempts,
            depends_on=list(action.depends_on),
            policy=HostActionPolicyDTO.from_model(action.policy),
            metadata=to_plain(action.metadata),
        )


class HostActionResultDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    action_type: str | None = None
    outcome: str = HostActionResultType.SUCCEEDED.value
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, result: HostActionResult) -> HostActionResultDTO:
        return cls(
            action_id=result.action_id,
            action_type=result.action_type,
            outcome=result.outcome.value,
            output=to_plain(result.output),
            error=result.error,
            metadata=to_plain(result.metadata),
        )

    def to_model(self) -> HostActionResult:
        return HostActionResult(
            action_id=self.action_id,
            action_type=self.action_type,
            outcome=HostActionResultType(self.outcome),
            output=dict(self.output),
            error=self.error,
            metadata=dict(self.metadata),
        )


class RecordHostActionResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant: str
    task_id: str
    result: HostActionResultDTO

    def to_model_result(self) -> HostActionResult:
        return self.result.to_model()
