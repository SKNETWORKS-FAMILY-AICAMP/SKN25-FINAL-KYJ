from __future__ import annotations

from dataclasses import dataclass, field

from ai_core.application.models.actions import HostAction, HostActionResult
from ai_core.application.models.tasks import TaskSnapshot
from ai_core.workflows.models.assistant import AssistantArtifacts, AssistantExecutionTrace


@dataclass(slots=True)
class WorkflowState:
    task: TaskSnapshot
    artifacts: AssistantArtifacts = field(default_factory=AssistantArtifacts)
    trace: AssistantExecutionTrace = field(default_factory=AssistantExecutionTrace)
    pending_actions: list[HostAction] = field(default_factory=list)
    last_action_result: HostActionResult | None = None
