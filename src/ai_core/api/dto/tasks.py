from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import Field

from ai_core.api.dto.actions import ActionPlanDTO, HostActionDTO
from ai_core.api.dto.base import APIBaseDTO, to_plain
from ai_core.api.dto.retrieval import (
    AssistantClarificationDTO,
    DocumentRecommendationResultDTO,
    DraftResultDTO,
    FolderRecommendationResultDTO,
    GeneratedTextResponse,
    RelatedRecommendationResultDTO,
)
from ai_core.application.models.actions import ActionPlan
from ai_core.application.models.results import (
    AssistantClarification,
    DocumentRecommendationResult,
    DraftResult,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from ai_core.application.models.tasks import (
    TaskAnalysis,
    TaskEvent,
    TaskEventType,
    TaskOutput,
    TaskOutputType,
    TaskRequest,
    TaskSnapshot,
    TaskStatus,
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
