from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict):
    state_version: int
    task: dict[str, Any]
    artifacts: dict[str, Any]
    trace: dict[str, Any]
    pending_actions: list[dict[str, Any]]
    last_action_result: dict[str, Any] | None
    query: dict[str, Any] | None
    plan: dict[str, Any] | None
    next_step_index: int
    needs_replan: bool
    retry_action_id: str | None
    failed_step_key: str | None
    last_error: str | None
    retry_counts: dict[str, int]
