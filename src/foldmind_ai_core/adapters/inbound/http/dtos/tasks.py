from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import Field

from foldmind_ai_core.adapters.inbound.http.dtos.actions import (
    ActionPlanDTO,
    HostActionDTO,
)
from foldmind_ai_core.adapters.inbound.http.dtos.dto_model import APIDTO
from foldmind_ai_core.adapters.inbound.http.dtos.workflow_outputs import (
    AssistantClarificationDTO,
    DocumentRecommendationResultDTO,
    DocumentSearchResultDTO,
    DraftResultDTO,
    FolderRecommendationResultDTO,
    GeneratedTextDTO,
    RelatedRecommendationResultDTO,
)


class TaskOutputMetaDTO(APIDTO):
    output_id: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClarificationOutputDTO(TaskOutputMetaDTO):
    type: Literal["clarification"] = "clarification"
    result: AssistantClarificationDTO


class DocumentRecommendationOutputDTO(TaskOutputMetaDTO):
    type: Literal["document_recommendation"] = "document_recommendation"
    result: DocumentRecommendationResultDTO


class DocumentSearchResultOutputDTO(TaskOutputMetaDTO):
    type: Literal["document_search_result"] = "document_search_result"
    result: DocumentSearchResultDTO


class FolderRecommendationOutputDTO(TaskOutputMetaDTO):
    type: Literal["folder_recommendation"] = "folder_recommendation"
    result: FolderRecommendationResultDTO


class RelatedRecommendationOutputDTO(TaskOutputMetaDTO):
    type: Literal["related_recommendation"] = "related_recommendation"
    result: RelatedRecommendationResultDTO


class AnswerOutputDTO(TaskOutputMetaDTO):
    type: Literal["answer"] = "answer"
    result: GeneratedTextDTO


class SummaryOutputDTO(TaskOutputMetaDTO):
    type: Literal["summary"] = "summary"
    result: GeneratedTextDTO


class DraftOutputDTO(TaskOutputMetaDTO):
    type: Literal["draft"] = "draft"
    result: DraftResultDTO


class IdeasOutputDTO(TaskOutputMetaDTO):
    type: Literal["ideas"] = "ideas"
    result: GeneratedTextDTO


class ActionPlanOutputDTO(TaskOutputMetaDTO):
    type: Literal["action_plan"] = "action_plan"
    result: ActionPlanDTO


TaskOutputDTO: TypeAlias = Annotated[
    ClarificationOutputDTO
    | DocumentRecommendationOutputDTO
    | DocumentSearchResultOutputDTO
    | FolderRecommendationOutputDTO
    | RelatedRecommendationOutputDTO
    | AnswerOutputDTO
    | SummaryOutputDTO
    | DraftOutputDTO
    | IdeasOutputDTO
    | ActionPlanOutputDTO,
    Field(discriminator="type"),
]


class TaskContextDTO(APIDTO):
    requested_at: str | None = None
    document_id: str | None = None
    folder_id: str | None = None


class CreateTaskRequest(APIDTO):
    tenant: str
    request: str
    context: TaskContextDTO | None = None


class AppendTaskInputRequest(APIDTO):
    request: str
    context: TaskContextDTO | None = None


class TaskEventDTO(APIDTO):
    event_id: str
    event_type: str
    message: str
    job_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class TaskAnalysisDTO(APIDTO):
    message: str


class TaskInputEntryDTO(APIDTO):
    task_input_id: str
    input_text: str
    context: TaskContextDTO
    position: int
    status: str


class TaskJobResultDTO(APIDTO):
    job_result_id: str
    result_type: str
    summary: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskJobDTO(APIDTO):
    job_id: str
    round_index: int
    position: int
    job_type: str
    status: str
    reason: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    results: list[TaskJobResultDTO] = Field(default_factory=list)


class TaskSnapshotDTO(APIDTO):
    task_id: str
    tenant: str
    request: str
    context: TaskContextDTO
    status: str
    analysis: TaskAnalysisDTO
    inputs: list[TaskInputEntryDTO] = Field(default_factory=list)
    jobs: list[TaskJobDTO] = Field(default_factory=list)
    result: TaskOutputDTO | None = None
    host_actions: list[HostActionDTO] = Field(default_factory=list)
    error: str | None = None
    current_action_id: str | None = None
    events: list[TaskEventDTO] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskSnapshotResponse(APIDTO):
    task: TaskSnapshotDTO


class RecordHostActionResultResponse(APIDTO):
    recorded: bool
    task: TaskSnapshotDTO
