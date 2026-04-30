from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from ai_core.api.dto._action_mappings import (
    expected_output_dto_type,
    host_action_output_from_model,
    host_action_type,
)
from ai_core.api.dto.action_outputs import HostActionResultOutputDTO
from ai_core.api.dto.base import APIBaseDTO
from ai_core.application.models.actions import (
    HostActionResult,
    HostActionResultType,
    HostActionType,
)


class HostActionResultDTO(APIBaseDTO):
    action_id: str
    action_type: HostActionType | None = None
    outcome: HostActionResultType
    output: HostActionResultOutputDTO | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_output_matches_action_type(self) -> HostActionResultDTO:
        if self.output is None:
            return self
        if self.action_type is None:
            raise ValueError("action_type is required when action result output is present.")

        expected_output_type = expected_output_dto_type(self.action_type)
        if not isinstance(self.output, expected_output_type):
            raise ValueError(
                f"{self.action_type} result requires {expected_output_type.__name__}."
            )
        return self

    @classmethod
    def from_model(cls, result: HostActionResult) -> HostActionResultDTO:
        action_type = (
            host_action_type(result.action_type)
            if result.action_type is not None
            else None
        )
        return cls(
            action_id=result.action_id,
            action_type=action_type,
            outcome=result.outcome,
            output=host_action_output_from_model(result.output),
            error=result.error,
            metadata=dict(result.metadata),
        )

    def to_model(self) -> HostActionResult:
        output = self.output.to_model() if self.output is not None else None
        return HostActionResult(
            action_id=self.action_id,
            outcome=self.outcome,
            action_type=str(self.action_type) if self.action_type is not None else None,
            output=output,
            error=self.error,
            metadata=dict(self.metadata),
        )


class RecordHostActionResultRequest(APIBaseDTO):
    tenant: str
    task_id: str
    result: HostActionResultDTO

    def to_model_result(self) -> HostActionResult:
        return self.result.to_model()


class RecordHostActionResultResponse(APIBaseDTO):
    recorded: bool
