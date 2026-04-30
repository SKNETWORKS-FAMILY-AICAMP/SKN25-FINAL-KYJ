from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_core.api.dto._plain import to_plain
from ai_core.api.dto.actions import HostActionDTO
from ai_core.application.models.tasks import (
    TaskAnalysis,
    TaskEvent,
    TaskRequest,
    TaskSnapshot,
)


class CreateTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class TaskEventDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, event: TaskEvent) -> TaskEventDTO:
        return cls(
            event_id=event.event_id,
            event_type=event.event_type.value,
            message=event.message,
            data=to_plain(event.data),
        )


class TaskAnalysisDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response: str
    clarification: dict[str, Any] | None = None
    document_recommendation: dict[str, Any] | None = None
    folder_recommendation: dict[str, Any] | None = None
    related_recommendation: dict[str, Any] | None = None
    answer: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    draft: dict[str, Any] | None = None
    ideas: dict[str, Any] | None = None
    action_plan: dict[str, Any] | None = None

    @classmethod
    def from_model(cls, analysis: TaskAnalysis) -> TaskAnalysisDTO:
        return cls(
            response=analysis.response,
            clarification=to_plain(analysis.clarification),
            document_recommendation=to_plain(analysis.document_recommendation),
            folder_recommendation=to_plain(analysis.folder_recommendation),
            related_recommendation=to_plain(analysis.related_recommendation),
            answer=to_plain(analysis.answer),
            summary=to_plain(analysis.summary),
            draft=to_plain(analysis.draft),
            ideas=to_plain(analysis.ideas),
            action_plan=to_plain(analysis.action_plan),
        )


class TaskSnapshotDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    tenant: str
    request: str
    status: str
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
            status=task.status.value,
            analysis=TaskAnalysisDTO.from_model(task.analysis),
            host_actions=[HostActionDTO.from_model(action) for action in task.host_actions],
            error=task.error,
            user_id=task.user_id,
            request_id=task.request_id,
            current_action_id=task.current_action_id,
            events=[TaskEventDTO.from_model(event) for event in task.events],
            metadata=to_plain(task.metadata),
        )


class TaskSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: TaskSnapshotDTO

    @classmethod
    def from_model(cls, task: TaskSnapshot) -> TaskSnapshotResponse:
        return cls(task=TaskSnapshotDTO.from_model(task))
