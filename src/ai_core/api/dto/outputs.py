from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import Field

from ai_core.api.dto._plain import to_plain
from ai_core.api.dto.action_plans import ActionPlanDTO
from ai_core.api.dto.base import APIBaseDTO
from ai_core.api.dto.generation import (
    AssistantClarificationDTO,
    DraftResultDTO,
    GeneratedTextResponse,
)
from ai_core.api.dto.recommendations import (
    DocumentRecommendationResultDTO,
    FolderRecommendationResultDTO,
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
from ai_core.application.models.tasks import TaskOutput, TaskOutputType


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
