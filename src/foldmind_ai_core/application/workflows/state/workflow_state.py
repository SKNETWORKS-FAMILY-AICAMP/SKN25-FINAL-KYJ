from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.application.workflows.state.execution import (
    WorkflowArtifacts,
    WorkflowExecutionPlan,
    WorkflowExecutionTrace,
)
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.workflow.actions import HostAction, HostActionResult
from foldmind_ai_core.domain.workflow.tasks import TaskSnapshot


@dataclass(slots=True)
class WorkflowState:
    task: TaskSnapshot
    artifacts: WorkflowArtifacts = field(default_factory=WorkflowArtifacts)
    trace: WorkflowExecutionTrace = field(default_factory=WorkflowExecutionTrace)
    pending_actions: list[HostAction] = field(default_factory=list)
    last_action_result: HostActionResult | None = None
    query: AIQuery | None = None
    plan: WorkflowExecutionPlan | None = None
    next_step_index: int = 0
    needs_replan: bool = False
    retry_action_id: str | None = None
    failed_step_key: str | None = None
    last_error: str | None = None
    retry_counts: dict[str, int] = field(default_factory=dict)
