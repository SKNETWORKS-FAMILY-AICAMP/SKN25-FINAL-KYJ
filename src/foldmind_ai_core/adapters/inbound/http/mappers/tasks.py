from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeAlias, cast

from foldmind_ai_core.adapters.inbound.http.dtos.dto_model import APIDTO
from foldmind_ai_core.adapters.inbound.http.dtos.tasks import (
    ActionPlanOutputDTO,
    AnswerOutputDTO,
    AppendTaskInputRequest,
    ClarificationOutputDTO,
    CreateTaskRequest,
    DocumentRecommendationOutputDTO,
    DocumentSearchResultOutputDTO,
    DraftOutputDTO,
    FolderRecommendationOutputDTO,
    IdeasOutputDTO,
    RecordHostActionResultResponse,
    RelatedRecommendationOutputDTO,
    SummaryOutputDTO,
    TaskAnalysisDTO,
    TaskContextDTO,
    TaskEventDTO,
    TaskInputEntryDTO,
    TaskJobDTO,
    TaskJobResultDTO,
    TaskOutputDTO,
    TaskOutputMetaDTO,
    TaskSnapshotDTO,
    TaskSnapshotResponse,
)
from foldmind_ai_core.adapters.inbound.http.mappers.actions import (
    action_plan_dto_from_domain,
    host_action_dto_from_domain,
)
from foldmind_ai_core.adapters.inbound.http.mappers.transport_values import (
    transport_value,
)
from foldmind_ai_core.adapters.inbound.http.mappers.workflow_outputs import (
    assistant_clarification_dto_from_result,
    document_recommendation_result_dto_from_result,
    document_search_result_dto_from_result,
    draft_result_dto_from_result,
    folder_recommendation_result_dto_from_result,
    generated_text_dto_from_result,
    related_recommendation_result_dto_from_result,
)
from foldmind_ai_core.core.application.models.task_commands import (
    AppendTaskInputCommand,
    CreateTaskCommand,
    GetTaskQuery,
    RemoveTaskInputCommand,
)
from foldmind_ai_core.core.application.models.generation import (
    AssistantClarification,
    DocumentRecommendationResult,
    DocumentSearchResult,
    DraftResult,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.core.domain.models.host_actions import ActionPlan
from foldmind_ai_core.core.application.models.task_results import (
    RecordActionResult,
)
from foldmind_ai_core.core.domain.models.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskEvent,
    TaskFinalResult,
    TaskInputEntry,
    TaskJob,
    TaskJobResult,
    TaskSnapshot,
)
from foldmind_ai_core.shared.validation import (
    InvalidInputError,
    require_aware_iso_timestamp,
    require_non_blank,
    require_optional_uuid,
    require_uuid,
    resolve_requested_at,
)

_TaskOutputConverter: TypeAlias = Callable[[Any], APIDTO]
_TaskOutputMapping: TypeAlias = tuple[
    type[object],
    type[TaskOutputMetaDTO],
    _TaskOutputConverter,
    str,
]

_TASK_OUTPUT_MAPPINGS: dict[str, _TaskOutputMapping] = {
    "clarification": (
        AssistantClarification,
        ClarificationOutputDTO,
        assistant_clarification_dto_from_result,
        "Clarification output requires AssistantClarification.",
    ),
    "document_recommendation": (
        DocumentRecommendationResult,
        DocumentRecommendationOutputDTO,
        document_recommendation_result_dto_from_result,
        "Document recommendation output requires DocumentRecommendationResult.",
    ),
    "document_search_result": (
        DocumentSearchResult,
        DocumentSearchResultOutputDTO,
        document_search_result_dto_from_result,
        "Document search result output requires DocumentSearchResult.",
    ),
    "folder_recommendation": (
        FolderRecommendationResult,
        FolderRecommendationOutputDTO,
        folder_recommendation_result_dto_from_result,
        "Folder recommendation output requires FolderRecommendationResult.",
    ),
    "related_recommendation": (
        RelatedRecommendationResult,
        RelatedRecommendationOutputDTO,
        related_recommendation_result_dto_from_result,
        "Related recommendation output requires RelatedRecommendationResult.",
    ),
    "answer": (
        GeneratedTextResult,
        AnswerOutputDTO,
        generated_text_dto_from_result,
        "Answer output requires GeneratedTextResult.",
    ),
    "summary": (
        GeneratedTextResult,
        SummaryOutputDTO,
        generated_text_dto_from_result,
        "Summary output requires GeneratedTextResult.",
    ),
    "draft": (
        DraftResult,
        DraftOutputDTO,
        draft_result_dto_from_result,
        "Draft output requires DraftResult.",
    ),
    "ideas": (
        GeneratedTextResult,
        IdeasOutputDTO,
        generated_text_dto_from_result,
        "Ideas output requires GeneratedTextResult.",
    ),
    "action_plan": (
        ActionPlan,
        ActionPlanOutputDTO,
        action_plan_dto_from_domain,
        "Action plan output requires ActionPlan.",
    ),
}
_INTERNAL_TASK_METADATA_KEYS = {"workflow_feedback", "workflow_round"}


def create_task_command_from_request(request: CreateTaskRequest) -> CreateTaskCommand:
    return CreateTaskCommand(
        tenant=require_non_blank(request.tenant, "tenant"),
        request=require_non_blank(request.request, "request"),
        context=task_context_from_dto(request.context),
    )


def append_task_command_from_request(
    *,
    task_id: str,
    request: AppendTaskInputRequest,
) -> AppendTaskInputCommand:
    return AppendTaskInputCommand(
        task_id=require_uuid(task_id, "task_id"),
        request=require_non_blank(request.request, "request"),
        context=task_context_from_dto(request.context),
    )


def get_task_query_from_path(*, task_id: str) -> GetTaskQuery:
    return GetTaskQuery(
        task_id=require_uuid(task_id, "task_id"),
    )


def remove_task_input_command_from_path(
    *,
    task_input_id: str,
) -> RemoveTaskInputCommand:
    return RemoveTaskInputCommand(
        task_input_id=require_uuid(task_input_id, "task_input_id"),
    )


def task_snapshot_response_from_result(
    task: TaskSnapshot,
) -> TaskSnapshotResponse:
    return TaskSnapshotResponse(task=task_snapshot_dto_from_result(task))


def record_action_result_response_from_result(
    result: RecordActionResult,
) -> RecordHostActionResultResponse:
    return RecordHostActionResultResponse(
        recorded=result.recorded,
        task=task_snapshot_dto_from_result(result.task),
    )


def task_snapshot_dto_from_result(task: TaskSnapshot) -> TaskSnapshotDTO:
    return TaskSnapshotDTO(
        task_id=task.task_id,
        tenant=task.tenant,
        request=task.request,
        context=task_context_dto_from_result(task.context),
        status=task.status.value,
        analysis=task_analysis_dto_from_result(task.analysis),
        inputs=[
            task_input_entry_dto_from_result(task_input)
            for task_input in task.inputs
        ],
        jobs=[task_job_dto_from_result(job) for job in task.jobs],
        result=(
            task_final_result_dto_from_result(task.result)
            if task.result is not None
            else None
        ),
        host_actions=[
            host_action_dto_from_domain(action)
            for action in task.host_actions
        ],
        error=task.error,
        current_action_id=task.current_action_id,
        events=[task_event_dto_from_result(event) for event in task.events],
        metadata=_public_task_metadata(task.metadata),
    )


def task_event_dto_from_result(event: TaskEvent) -> TaskEventDTO:
    return TaskEventDTO(
        event_id=event.event_id,
        event_type=event.event_type.value,
        message=event.message,
        job_id=event.job_id,
        data=transport_value(event.data),
    )


def task_analysis_dto_from_result(analysis: TaskAnalysis) -> TaskAnalysisDTO:
    return TaskAnalysisDTO(message=analysis.message)


def task_input_entry_dto_from_result(task_input: TaskInputEntry) -> TaskInputEntryDTO:
    return TaskInputEntryDTO(
        task_input_id=task_input.task_input_id,
        input_text=task_input.input_text,
        context=task_context_dto_from_result(task_input.context),
        position=task_input.position,
        status=task_input.status.value,
    )


def task_job_dto_from_result(job: TaskJob) -> TaskJobDTO:
    return TaskJobDTO(
        job_id=job.job_id,
        round_index=job.round_index,
        position=job.position,
        job_type=job.job_type,
        status=job.status.value,
        reason=job.reason,
        input=transport_value(job.input),
        started_at=job.started_at,
        finished_at=job.finished_at,
        error=job.error,
        metadata=transport_value(job.metadata),
        results=[task_job_result_dto_from_result(result) for result in job.results],
    )


def task_job_result_dto_from_result(
    result: TaskJobResult,
) -> TaskJobResultDTO:
    return TaskJobResultDTO(
        job_result_id=result.job_result_id,
        result_type=result.result_type,
        summary=transport_value(result.summary),
        metadata=transport_value(result.metadata),
    )


def task_final_result_dto_from_result(result: TaskFinalResult) -> TaskOutputDTO:
    return task_output_dto_from_result(
        output_type=result.result_type.value,
        result=result.result,
        title=result.title,
        metadata=result.metadata,
    )


def task_context_from_dto(dto: TaskContextDTO | None) -> TaskContext:
    if dto is None:
        return TaskContext(requested_at=resolve_requested_at(None))
    if dto.requested_at is None and dto.document_id is None and dto.folder_id is None:
        raise InvalidInputError(
            "context must include requested_at, document_id, or folder_id."
        )
    return TaskContext(
        requested_at=(
            require_aware_iso_timestamp(dto.requested_at, "context.requested_at")
            if dto.requested_at is not None
            else resolve_requested_at(None)
        ),
        document_id=require_optional_uuid(dto.document_id, "context.document_id"),
        folder_id=require_optional_uuid(dto.folder_id, "context.folder_id"),
    )


def task_context_dto_from_result(context: TaskContext) -> TaskContextDTO:
    return TaskContextDTO(
        requested_at=context.requested_at,
        document_id=context.document_id,
        folder_id=context.folder_id,
    )


def task_output_dto_from_result(
    *,
    output_type: str,
    result: object,
    output_id: str | None = None,
    title: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> TaskOutputDTO:
    output_fields = {
        "output_id": output_id,
        "title": title,
        "metadata": transport_value(metadata or {}),
    }
    mapping = _TASK_OUTPUT_MAPPINGS.get(output_type)
    if mapping is None:
        raise TypeError(f"Unsupported task result type: {output_type}")
    result_type, dto_type, converter, error_message = mapping
    if not isinstance(result, result_type):
        raise TypeError(error_message)
    dto_class = cast(Any, dto_type)
    return cast(
        TaskOutputDTO,
        dto_class(**output_fields, result=converter(result)),
    )


def _public_task_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        key: transport_value(value)
        for key, value in metadata.items()
        if key not in _INTERNAL_TASK_METADATA_KEYS
    }
