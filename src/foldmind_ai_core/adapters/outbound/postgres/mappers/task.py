from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import cast

from foldmind_ai_core.adapters.outbound.workflow_model_codec import (
    restore_workflow_model_json,
    workflow_model_json,
)
from foldmind_ai_core.adapters.outbound.postgres.models.task import (
    HostActionRow,
    TaskEventRow,
    TaskInputRow,
    TaskJobResultRow,
    TaskJobRow,
    TaskRow,
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
from foldmind_ai_core.core.domain.models.host_actions import (
    ActionPlan,
    CreateDocumentInput,
    CreateFolderInput,
    HostAction,
    HostActionPolicy,
    HostActionStatus,
    HostActionType,
    LinkDocumentsInput,
    MoveDocumentInput,
    UpdateDocumentInput,
)
from foldmind_ai_core.core.domain.models.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskEvent,
    TaskEventType,
    TaskFinalResult,
    TaskInputEntry,
    TaskInputStatus,
    TaskJob,
    TaskJobResult,
    TaskJobStatus,
    TaskOutputType,
    TaskOutputValue,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.shared.internal_ids import stable_internal_id
from foldmind_ai_core.shared.types import JsonObject, Metadata

_RESULT_TYPE_BY_OUTPUT_TYPE = {
    TaskOutputType.CLARIFICATION: AssistantClarification,
    TaskOutputType.DOCUMENT_RECOMMENDATION: DocumentRecommendationResult,
    TaskOutputType.DOCUMENT_SEARCH_RESULT: DocumentSearchResult,
    TaskOutputType.FOLDER_RECOMMENDATION: FolderRecommendationResult,
    TaskOutputType.RELATED_RECOMMENDATION: RelatedRecommendationResult,
    TaskOutputType.ANSWER: GeneratedTextResult,
    TaskOutputType.SUMMARY: GeneratedTextResult,
    TaskOutputType.DRAFT: DraftResult,
    TaskOutputType.IDEAS: GeneratedTextResult,
    TaskOutputType.ACTION_PLAN: ActionPlan,
}

_INPUT_TYPE_BY_ACTION_TYPE = {
    HostActionType.CREATE_FOLDER: CreateFolderInput,
    HostActionType.CREATE_DOCUMENT: CreateDocumentInput,
    HostActionType.UPDATE_DOCUMENT: UpdateDocumentInput,
    HostActionType.MOVE_DOCUMENT: MoveDocumentInput,
    HostActionType.LINK_DOCUMENTS: LinkDocumentsInput,
}

_TERMINAL_TASK_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.REJECTED,
}


def task_row_from_snapshot(snapshot: TaskSnapshot) -> TaskRow:
    result = snapshot.result
    return TaskRow(
        task_id=snapshot.task_id,
        tenant=snapshot.tenant,
        request_text=snapshot.request,
        context_json=task_context_json(snapshot.context),
        status=str(snapshot.status),
        analysis_message=snapshot.analysis.message,
        result_type=str(result.result_type) if result is not None else None,
        result_json=_model_json(result.result) if result is not None else None,
        result_title=result.title if result is not None else None,
        result_metadata=dict(result.metadata) if result is not None else {},
        current_action_id=snapshot.current_action_id,
        error_json={"message": snapshot.error} if snapshot.error is not None else None,
        completed_at=(
            datetime.now(UTC)
            if snapshot.status in _TERMINAL_TASK_STATUSES
            else None
        ),
        metadata_json=dict(snapshot.metadata),
    )


def task_input_rows_from_snapshot(
    snapshot: TaskSnapshot,
) -> tuple[TaskInputRow, ...]:
    return tuple(
        TaskInputRow(
            task_input_id=task_input.task_input_id,
            task_id=snapshot.task_id,
            input_text=task_input.input_text,
            context_json=task_context_json(task_input.context),
            position=task_input.position,
            status=str(task_input.status),
            deleted_at=(
                datetime.now(UTC)
                if task_input.status == TaskInputStatus.REMOVED
                else None
            ),
        )
        for task_input in sorted(snapshot.inputs, key=lambda item: item.position)
    )


def task_job_rows_from_snapshot(
    snapshot: TaskSnapshot,
) -> tuple[TaskJobRow, ...]:
    return tuple(
        TaskJobRow(
            job_id=job.job_id,
            task_id=snapshot.task_id,
            round_index=job.round_index,
            position=job.position,
            job_type=job.job_type,
            status=str(job.status),
            reason=job.reason,
            input_json=dict(job.input),
            started_at=job.started_at,
            finished_at=job.finished_at,
            error_json={"message": job.error} if job.error is not None else None,
            metadata_json=dict(job.metadata),
        )
        for job in sorted(snapshot.jobs, key=lambda item: (item.round_index, item.position))
    )


def task_job_result_rows_from_snapshot(
    snapshot: TaskSnapshot,
) -> tuple[TaskJobResultRow, ...]:
    rows: list[TaskJobResultRow] = []
    for job in sorted(snapshot.jobs, key=lambda item: (item.round_index, item.position)):
        for position, result in enumerate(job.results):
            rows.append(
                TaskJobResultRow(
                    job_result_id=result.job_result_id,
                    job_id=job.job_id,
                    position=position,
                    result_type=result.result_type,
                    result_json=_job_result_json(result),
                    summary_json=dict(result.summary),
                    metadata_json=dict(result.metadata),
                )
            )
    return tuple(rows)


def host_action_rows_from_snapshot(
    snapshot: TaskSnapshot,
) -> tuple[HostActionRow, ...]:
    return tuple(
        HostActionRow(
            action_id=_action_id(action, position, snapshot.task_id),
            task_id=snapshot.task_id,
            job_id=action.job_id,
            position=position,
            action_type=str(action.action_type),
            summary=action.summary,
            input_json=_model_json(action.input),
            reason=action.reason,
            status=str(action.status),
            attempts=action.attempts,
            policy_json=_model_json(action.policy),
            metadata_json=dict(action.metadata),
        )
        for position, action in enumerate(snapshot.host_actions)
    )


def task_event_rows_from_snapshot(
    snapshot: TaskSnapshot,
) -> tuple[TaskEventRow, ...]:
    return tuple(
        TaskEventRow(
            event_id=event.event_id,
            task_id=snapshot.task_id,
            event_type=str(event.event_type),
            message=event.message,
            job_id=event.job_id,
            data_json=dict(event.data),
        )
        for event in snapshot.events
    )


def task_snapshot_from_rows(
    *,
    task: TaskRow,
    inputs: tuple[TaskInputRow, ...],
    jobs: tuple[TaskJobRow, ...],
    job_results: tuple[TaskJobResultRow, ...],
    host_actions: tuple[HostActionRow, ...],
    events: tuple[TaskEventRow, ...],
) -> TaskSnapshot:
    return TaskSnapshot(
        task_id=task.task_id,
        tenant=task.tenant,
        request=task.request_text,
        context=task_context_from_json(task.context_json),
        status=TaskStatus(task.status),
        analysis=TaskAnalysis(message=task.analysis_message),
        inputs=[task_input_from_row(task_input) for task_input in inputs],
        jobs=task_jobs_from_rows(jobs=jobs, job_results=job_results),
        result=task_final_result_from_row(task),
        host_actions=host_actions_from_rows(host_actions),
        error=error_text(task.error_json),
        current_action_id=_optional_task_text(
            task.current_action_id,
            "current_action_id",
        ),
        events=[task_event_from_row(event) for event in events],
        metadata=metadata(task.metadata_json),
    )


def task_input_from_row(row: TaskInputRow) -> TaskInputEntry:
    return TaskInputEntry(
        task_input_id=row.task_input_id,
        task_id=row.task_id,
        input_text=row.input_text,
        context=task_context_from_json(row.context_json),
        position=row.position,
        status=TaskInputStatus(row.status),
    )


def task_jobs_from_rows(
    *,
    jobs: tuple[TaskJobRow, ...],
    job_results: tuple[TaskJobResultRow, ...],
) -> list[TaskJob]:
    results_by_job: dict[str, list[TaskJobResultRow]] = defaultdict(list)
    for result in job_results:
        results_by_job[result.job_id].append(result)
    return [
        task_job_from_row(job, tuple(results_by_job[job.job_id]))
        for job in sorted(jobs, key=lambda item: (item.round_index, item.position))
    ]


def task_job_from_row(
    row: TaskJobRow,
    results: tuple[TaskJobResultRow, ...],
) -> TaskJob:
    return TaskJob(
        job_id=row.job_id,
        job_type=row.job_type,
        round_index=row.round_index,
        position=row.position,
        status=TaskJobStatus(row.status),
        reason=row.reason,
        input=row.input_json,
        started_at=_optional_timestamp_text(row.started_at),
        finished_at=_optional_timestamp_text(row.finished_at),
        error=error_text(row.error_json),
        metadata=metadata(row.metadata_json),
        results=[
            task_job_result_from_row(result)
            for result in sorted(results, key=lambda item: item.position)
        ],
    )


def task_job_result_from_row(row: TaskJobResultRow) -> TaskJobResult:
    return TaskJobResult(
        job_result_id=row.job_result_id,
        result_type=row.result_type,
        result=job_result_value(row.result_type, row.result_json),
        summary=row.summary_json,
        metadata=metadata(row.metadata_json),
    )


def task_final_result_from_row(task: TaskRow) -> TaskFinalResult | None:
    if task.result_type is None or task.result_json is None:
        return None
    output_type = TaskOutputType(task.result_type)
    return TaskFinalResult(
        result_type=output_type,
        result=output_result_value(output_type, task.result_json),
        title=task.result_title,
        metadata=metadata(task.result_metadata),
    )


def task_context_json(context: TaskContext) -> JsonObject:
    return {
        "requested_at": context.requested_at,
        "document_id": context.document_id,
        "folder_id": context.folder_id,
    }


def task_context_from_json(value: object) -> TaskContext:
    if not isinstance(value, dict):
        raise ValueError("context_json must contain a JSON object.")
    requested_at = value.get("requested_at")
    document_id = value.get("document_id")
    folder_id = value.get("folder_id")
    if not isinstance(requested_at, str):
        raise ValueError("context_json.requested_at must be a string.")
    if document_id is not None and not isinstance(document_id, str):
        raise ValueError("context_json.document_id must be a string or null.")
    if folder_id is not None and not isinstance(folder_id, str):
        raise ValueError("context_json.folder_id must be a string or null.")
    return TaskContext(
        requested_at=requested_at,
        document_id=document_id,
        folder_id=folder_id,
    )


def host_actions_from_rows(action_rows: tuple[HostActionRow, ...]) -> list[HostAction]:
    actions: list[HostAction] = []
    for row in action_rows:
        action_type = HostActionType(row.action_type)
        input_type = _INPUT_TYPE_BY_ACTION_TYPE[action_type]
        actions.append(
            HostAction(
                action_type=action_type,
                summary=row.summary,
                input=restore_workflow_model_json(row.input_json, input_type),
                action_id=row.action_id,
                job_id=row.job_id,
                reason=row.reason,
                status=HostActionStatus(row.status),
                attempts=row.attempts,
                policy=restore_workflow_model_json(row.policy_json, HostActionPolicy),
                metadata=metadata(row.metadata_json),
            )
        )
    return actions


def task_event_from_row(row: TaskEventRow) -> TaskEvent:
    return TaskEvent(
        event_id=row.event_id,
        event_type=TaskEventType(row.event_type),
        message=row.message,
        data=metadata(row.data_json),
        job_id=row.job_id,
    )


def output_result_value(output_type: TaskOutputType, value: JsonObject) -> TaskOutputValue:
    result_type = _RESULT_TYPE_BY_OUTPUT_TYPE[output_type]
    return restore_workflow_model_json(value, result_type)


def job_result_value(result_type: str, value: JsonObject) -> TaskOutputValue | JsonObject:
    try:
        output_type = TaskOutputType(result_type)
    except ValueError:
        return value
    return output_result_value(output_type, value)


def metadata(value: object) -> Metadata:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("metadata fields must contain JSON objects.")
    return cast(Metadata, value)


def error_text(value: object) -> str | None:
    if isinstance(value, dict):
        message = value.get("message")
        if isinstance(message, str) and message:
            return message
    return None


def _optional_timestamp_text(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def _model_json(value: object) -> JsonObject:
    return cast(JsonObject, workflow_model_json(value))


def _job_result_json(result: TaskJobResult) -> JsonObject:
    if isinstance(result.result, dict):
        return cast(JsonObject, dict(result.result))
    return _model_json(result.result)


def _action_id(action: HostAction, position: int, task_id: str) -> str:
    return action.action_id or stable_internal_id("host-action", task_id, position)


def _metadata_json_object(value: object) -> JsonObject:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("metadata fields must contain JSON objects.")
    return cast(JsonObject, value)


def _optional_task_text(value: object, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    return value or None
