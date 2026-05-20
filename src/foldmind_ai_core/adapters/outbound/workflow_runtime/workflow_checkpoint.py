from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

CHECKPOINT_STATE_VERSION = 1


class WorkflowCheckpointState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    state_version: int = CHECKPOINT_STATE_VERSION
    task: dict[str, Any]
    artifacts: dict[str, Any]
    trace: dict[str, Any]
    pending_actions: list[dict[str, Any]]
    last_action_result: dict[str, Any] | None = None
    query: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    next_step_index: int = 0
    needs_replan: bool = False
    retry_action_id: str | None = None
    failed_step_key: str | None = None
    last_error: str | None = None
    retry_counts: dict[str, int] = Field(default_factory=dict)

    @field_validator("next_step_index")
    @classmethod
    def validate_next_step_index(cls, value: int) -> int:
        if value < 0:
            raise ValueError("next_step_index must be non-negative.")
        return value

    @field_validator("retry_counts")
    @classmethod
    def validate_retry_counts(cls, value: dict[str, int]) -> dict[str, int]:
        if any(count < 0 for count in value.values()):
            raise ValueError("retry_counts values must be non-negative.")
        return value
