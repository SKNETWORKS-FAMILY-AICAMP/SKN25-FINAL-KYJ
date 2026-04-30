from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.models.actions import HostAction, HostActionStatus
from ai_core.application.models.tasks import TaskSnapshot


@dataclass(slots=True)
class ActionDeciderAgent:
    def next_action(self, task: TaskSnapshot) -> HostAction | None:
        for action in task.host_actions:
            if action.status == HostActionStatus.PROPOSED:
                action.status = HostActionStatus.READY
                return action
        return None
