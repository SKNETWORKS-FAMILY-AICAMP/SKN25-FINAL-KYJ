from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

CHECKPOINT_STATE_VERSION = 1


class WorkflowCheckpointState(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
