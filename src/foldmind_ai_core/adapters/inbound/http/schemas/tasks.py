from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import Field

from foldmind_ai_core.adapters.inbound.http.schemas.actions import ActionPlanDTO, HostActionDTO
from foldmind_ai_core.adapters.inbound.http.schemas.base import APIBaseDTO, to_plain
from foldmind_ai_core.adapters.inbound.http.schemas.retrieval import (
    AssistantClarificationDTO,
    DocumentRecommendationResultDTO,
    DraftResultDTO,
    FolderRecommendationResultDTO,
    GeneratedTextResponse,
    RelatedRecommendationResultDTO,
)
from foldmind_ai_core.domain.generation.results import (
    AssistantClarification,
    DocumentRecommendationResult,
    DraftResult,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.domain.workflow.actions import ActionPlan
from foldmind_ai_core.domain.workflow.tasks import (
    TaskAnalysis,
    TaskAppendRequest as DomainTaskAppendRequest,
    TaskCreationRequest,
    TaskEvent,
    TaskEventType,
    TaskOutput,
    TaskOutputType,
    TaskRequestEntry,
    TaskRequestStatus,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.shared.validation import (
    require_non_blank,
    require_uuid,
)


class TaskOutputMetaDTO(APIBaseDTO):
    output_id: str | None = None
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClarificationOutputDTO(TaskOutputMetaDTO):
    type: Literal["clarification"] = "clarification"
    result: AssistantClarificationDTO


class DocumentRecommendationOutputDTO(TaskOutputMetaDTO):
    type: Literal["document_recommendation"] = "document_recommendation"
    result: DocumentRecommendationResultDTO


class FolderRecommendationOutputDTO(TaskOutputMetaDTO):
    type: Literal["folder_recommendation"] = "folder_recommendation"
    result: FolderRecommendationResultDTO


class RelatedRecommendationOutputDTO(TaskOutputMetaDTO):
    type: Literal["related_recommendation"] = "related_recommendation"
    result: RelatedRecommendationResultDTO


class AnswerOutputDTO(TaskOutputMetaDTO):
    type: Literal["answer"] = "answer"
    result: GeneratedTextResponse


class SummaryOutputDTO(TaskOutputMetaDTO):
    type: Literal["summary"] = "summary"
    result: GeneratedTextResponse


class DraftOutputDTO(TaskOutputMetaDTO):
    type: Literal["draft"] = "draft"
    result: DraftResultDTO


class IdeasOutputDTO(TaskOutputMetaDTO):
    type: Literal["ideas"] = "ideas"
    result: GeneratedTextResponse


class ActionPlanOutputDTO(TaskOutputMetaDTO):
    type: Literal["action_plan"] = "action_plan"
    result: ActionPlanDTO


TaskOutputDTO: TypeAlias = Annotated[
    ClarificationOutputDTO
    | DocumentRecommendationOutputDTO
    | FolderRecommendationOutputDTO
    | RelatedRecommendationOutputDTO
    | AnswerOutputDTO
    | SummaryOutputDTO
    | DraftOutputDTO
    | IdeasOutputDTO
    | ActionPlanOutputDTO,
    Field(discriminator="type"),
]


def task_output_from_model(output: TaskOutput) -> TaskOutputDTO:
    common = {
        "output_id": output.output_id,
        "title": output.title,
        "metadata": to_plain(output.metadata),
    }
    match output.output_type:
        case TaskOutputType.CLARIFICATION:
            if not isinstance(output.result, AssistantClarification):
                raise TypeError("Clarification output requires AssistantClarification result.")
            return ClarificationOutputDTO(
                **common,
                result=AssistantClarificationDTO.from_model(output.result),
            )
        case TaskOutputType.DOCUMENT_RECOMMENDATION:
            if not isinstance(output.result, DocumentRecommendationResult):
                raise TypeError(
                    "Document recommendation output requires DocumentRecommendationResult."
                )
            return DocumentRecommendationOutputDTO(
                **common,
                result=DocumentRecommendationResultDTO.from_model(output.result),
            )
        case TaskOutputType.FOLDER_RECOMMENDATION:
            if not isinstance(output.result, FolderRecommendationResult):
                raise TypeError(
                    "Folder recommendation output requires FolderRecommendationResult."
                )
            return FolderRecommendationOutputDTO(
                **common,
                result=FolderRecommendationResultDTO.from_model(output.result),
            )
        case TaskOutputType.RELATED_RECOMMENDATION:
            if not isinstance(output.result, RelatedRecommendationResult):
                raise TypeError(
                    "Related recommendation output requires RelatedRecommendationResult."
                )
            return RelatedRecommendationOutputDTO(
                **common,
                result=RelatedRecommendationResultDTO.from_model(output.result),
            )
        case TaskOutputType.ANSWER:
            if not isinstance(output.result, GeneratedTextResult):
                raise TypeError("Answer output requires GeneratedTextResult.")
            return AnswerOutputDTO(
                **common,
                result=GeneratedTextResponse.from_model(output.result),
            )
        case TaskOutputType.SUMMARY:
            if not isinstance(output.result, GeneratedTextResult):
                raise TypeError("Summary output requires GeneratedTextResult.")
            return SummaryOutputDTO(
                **common,
                result=GeneratedTextResponse.from_model(output.result),
            )
        case TaskOutputType.DRAFT:
            if not isinstance(output.result, DraftResult):
                raise TypeError("Draft output requires DraftResult.")
            return DraftOutputDTO(**common, result=DraftResultDTO.from_model(output.result))
        case TaskOutputType.IDEAS:
            if not isinstance(output.result, GeneratedTextResult):
                raise TypeError("Ideas output requires GeneratedTextResult.")
            return IdeasOutputDTO(
                **common,
                result=GeneratedTextResponse.from_model(output.result),
            )
        case TaskOutputType.ACTION_PLAN:
            if not isinstance(output.result, ActionPlan):
                raise TypeError("Action plan output requires ActionPlan.")
            return ActionPlanOutputDTO(**common, result=ActionPlanDTO.from_model(output.result))


def public_task_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    internal_keys = {"workflow_round"}
    return {
        key: to_plain(value)
        for key, value in metadata.items()
        if key not in internal_keys
    }


class CreateTaskRequest(APIBaseDTO):
    tenant: str
    request: str

    def to_model(self) -> TaskCreationRequest:
        require_non_blank(self.tenant, "tenant")
        require_non_blank(self.request, "request")
        return TaskCreationRequest(
            tenant=self.tenant,
            request=self.request,
        )


class AppendTaskRequest(APIBaseDTO):
    request: str

    def to_model(self, *, task_id: str) -> DomainTaskAppendRequest:
        require_uuid(task_id, "task_id")
        require_non_blank(self.request, "request")
        return DomainTaskAppendRequest(
            task_id=task_id,
            request=self.request,
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


class TaskRequestEntryDTO(APIBaseDTO):
    task_request_id: str
    request: str
    position: int
    status: TaskRequestStatus

    @classmethod
    def from_model(cls, request: TaskRequestEntry) -> TaskRequestEntryDTO:
        return cls(
            task_request_id=request.task_request_id,
            request=request.request,
            position=request.position,
            status=request.status,
        )


class TaskSnapshotDTO(APIBaseDTO):
    task_id: str
    tenant: str
    request: str
    status: TaskStatus
    analysis: TaskAnalysisDTO
    requests: list[TaskRequestEntryDTO] = Field(default_factory=list)
    host_actions: list[HostActionDTO] = Field(default_factory=list)
    error: str | None = None
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
            requests=[TaskRequestEntryDTO.from_model(request) for request in task.requests],
            host_actions=[HostActionDTO.from_model(action) for action in task.host_actions],
            error=task.error,
            current_action_id=task.current_action_id,
            events=[TaskEventDTO.from_model(event) for event in task.events],
            metadata=public_task_metadata(task.metadata),
        )


class TaskSnapshotResponse(APIBaseDTO):
    task: TaskSnapshotDTO

    @classmethod
    def from_model(cls, task: TaskSnapshot) -> TaskSnapshotResponse:
        return cls(task=TaskSnapshotDTO.from_model(task))


class RecordHostActionResultResponse(APIBaseDTO):
    recorded: bool
    task: TaskSnapshotDTO
