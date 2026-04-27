from __future__ import annotations

from dataclasses import dataclass, field

from ai_core.domain.actions import HostAction, HostActionResult
from ai_core.domain.tasks import AssistantArtifacts, AssistantExecutionTrace, TaskSnapshot


@dataclass(slots=True)
class WorkflowState:
    task: TaskSnapshot
    artifacts: AssistantArtifacts = field(default_factory=AssistantArtifacts)
    trace: AssistantExecutionTrace = field(default_factory=AssistantExecutionTrace)
    pending_actions: list[HostAction] = field(default_factory=list)
    last_action_result: HostActionResult | None = None
