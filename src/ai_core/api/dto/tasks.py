from __future__ import annotations

from typing import Any

from pydantic import Field

from ai_core.api.dto._plain import to_plain
from ai_core.api.dto.action_plans import HostActionDTO
from ai_core.api.dto.base import APIBaseDTO
from ai_core.api.dto.outputs import TaskOutputDTO, task_output_from_model
from ai_core.application.models.tasks import (
    TaskAnalysis,
    TaskEvent,
    TaskEventType,
    TaskRequest,
    TaskSnapshot,
    TaskStatus,
)


class CreateTaskRequest(APIBaseDTO):
    task_id: str
    tenant: str
    request: str
    user_id: str | None = None
    request_id: str | None = None
    conversation_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)

    def to_model(self) -> TaskRequest:
        return TaskRequest(
            task_id=self.task_id,
            tenant=self.tenant,
            request=self.request,
            user_id=self.user_id,
            request_id=self.request_id,
            conversation_id=self.conversation_id,
            context=dict(self.context),
        )


class TaskEventDTO(APIBaseDTO):
    event_id: str
    event_type: TaskEventType
    message: str
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, event: TaskEvent) -> TaskEventDTO:
        return cls(
            event_id=event.event_id,
            event_type=event.event_type,
            message=event.message,
            data=to_plain(event.data),
        )


class TaskAnalysisDTO(APIBaseDTO):
    message: str
    outputs: list[TaskOutputDTO] = Field(default_factory=list)

    @classmethod
    def from_model(cls, analysis: TaskAnalysis) -> TaskAnalysisDTO:
        return cls(
            message=analysis.message,
            outputs=[task_output_from_model(output) for output in analysis.outputs],
        )


class TaskSnapshotDTO(APIBaseDTO):
    task_id: str
    tenant: str
    request: str
    status: TaskStatus
    analysis: TaskAnalysisDTO
    host_actions: list[HostActionDTO] = Field(default_factory=list)
    error: str | None = None
    user_id: str | None = None
    request_id: str | None = None
    current_action_id: str | None = None
    events: list[TaskEventDTO] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, task: TaskSnapshot) -> TaskSnapshotDTO:
        return cls(
            task_id=task.task_id,
            tenant=task.tenant,
            request=task.request,
            status=task.status,
            analysis=TaskAnalysisDTO.from_model(task.analysis),
            host_actions=[HostActionDTO.from_model(action) for action in task.host_actions],
            error=task.error,
            user_id=task.user_id,
            request_id=task.request_id,
            current_action_id=task.current_action_id,
            events=[TaskEventDTO.from_model(event) for event in task.events],
            metadata=to_plain(task.metadata),
        )


class TaskSnapshotResponse(APIBaseDTO):
    task: TaskSnapshotDTO

    @classmethod
    def from_model(cls, task: TaskSnapshot) -> TaskSnapshotResponse:
        return cls(task=TaskSnapshotDTO.from_model(task))
