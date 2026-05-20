from __future__ import annotations

from collections import defaultdict
from typing import cast

from foldmind_ai_core.adapters.outbound.domain_model_codec import (
    domain_model_json,
    restore_domain_model_json,
)
from foldmind_ai_core.adapters.outbound.postgres.models.task import (
    PostgresHostActionRecord,
    PostgresTaskEventRecord,
    PostgresTaskInputRecord,
    PostgresTaskJobRecord,
    PostgresTaskJobResultRecord,
    PostgresTaskRecord,
)
from foldmind_ai_core.core.domain.models.generation.results import (
    AssistantClarification,
    DocumentRecommendationResult,
    DocumentSearchResult,
    DraftResult,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.core.domain.models.workflow.actions import (
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
from foldmind_ai_core.core.domain.models.workflow.tasks import (
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
    TaskOutputResult,
    TaskOutputType,
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


def task_record_from_snapshot(snapshot: TaskSnapshot) -> PostgresTaskRecord:
    result = snapshot.result
    return PostgresTaskRecord(
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
        metadata=dict(snapshot.metadata),
    )


def task_input_records_from_snapshot(
    snapshot: TaskSnapshot,
) -> tuple[PostgresTaskInputRecord, ...]:
    return tuple(
        PostgresTaskInputRecord(
            task_input_id=task_input.task_input_id,
            task_id=snapshot.task_id,
            input_text=task_input.input_text,
            context_json=task_context_json(task_input.context),
            position=task_input.position,
            status=str(task_input.status),
        )
        for task_input in sorted(snapshot.inputs, key=lambda item: item.position)
    )


def task_job_records_from_snapshot(
    snapshot: TaskSnapshot,
) -> tuple[PostgresTaskJobRecord, ...]:
    return tuple(
        PostgresTaskJobRecord(
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
            metadata=dict(job.metadata),
        )
        for job in sorted(snapshot.jobs, key=lambda item: (item.round_index, item.position))
    )


def task_job_result_records_from_snapshot(
    snapshot: TaskSnapshot,
) -> tuple[PostgresTaskJobResultRecord, ...]:
    records: list[PostgresTaskJobResultRecord] = []
    for job in sorted(snapshot.jobs, key=lambda item: (item.round_index, item.position)):
        for position, result in enumerate(job.results):
            records.append(
                PostgresTaskJobResultRecord(
                    job_result_id=result.job_result_id,
                    job_id=job.job_id,
                    position=position,
                    result_type=result.result_type,
                    result_json=_job_result_json(result),
                    summary_json=dict(result.summary),
                    metadata=dict(result.metadata),
                )
            )
    return tuple(records)


def host_action_records_from_snapshot(
    snapshot: TaskSnapshot,
) -> tuple[PostgresHostActionRecord, ...]:
    return tuple(
        PostgresHostActionRecord(
            action_id=_action_id(action, position, snapshot.task_id),
            job_id=action.job_id,
            action_type=str(action.action_type),
            summary=action.summary,
            input_json=_model_json(action.input),
            reason=action.reason,
            status=str(action.status),
            attempts=action.attempts,
            policy_json=_model_json(action.policy),
            metadata=dict(action.metadata),
        )
        for position, action in enumerate(snapshot.host_actions)
    )


def task_event_records_from_snapshot(
    snapshot: TaskSnapshot,
) -> tuple[PostgresTaskEventRecord, ...]:
    return tuple(
        PostgresTaskEventRecord(
            event_id=event.event_id,
            event_type=str(event.event_type),
            message=event.message,
            job_id=event.job_id,
            data_json=dict(event.data),
        )
        for event in snapshot.events
    )


def task_snapshot_from_records(
    *,
    task: PostgresTaskRecord,
    inputs: tuple[PostgresTaskInputRecord, ...],
    jobs: tuple[PostgresTaskJobRecord, ...],
    job_results: tuple[PostgresTaskJobResultRecord, ...],
    host_actions: tuple[PostgresHostActionRecord, ...],
    events: tuple[PostgresTaskEventRecord, ...],
) -> TaskSnapshot:
    return TaskSnapshot(
        task_id=task.task_id,
        tenant=task.tenant,
        request=task.request_text,
        context=task_context_from_json(task.context_json),
        status=TaskStatus(task.status),
        analysis=TaskAnalysis(message=task.analysis_message),
        inputs=[task_input_from_record(task_input) for task_input in inputs],
        jobs=task_jobs_from_records(jobs=jobs, job_results=job_results),
        result=task_final_result_from_record(task),
        host_actions=host_actions_from_records(host_actions),
        error=error_text(task.error_json),
        current_action_id=task.current_action_id,
        events=[task_event_from_record(event) for event in events],
        metadata=metadata(task.metadata),
    )


def task_input_from_record(record: PostgresTaskInputRecord) -> TaskInputEntry:
    return TaskInputEntry(
        task_input_id=record.task_input_id,
        task_id=record.task_id,
        input_text=record.input_text,
        context=task_context_from_json(record.context_json),
        position=record.position,
        status=TaskInputStatus(record.status),
    )


def task_jobs_from_records(
    *,
    jobs: tuple[PostgresTaskJobRecord, ...],
    job_results: tuple[PostgresTaskJobResultRecord, ...],
) -> list[TaskJob]:
    results_by_job: dict[str, list[PostgresTaskJobResultRecord]] = defaultdict(list)
    for result in job_results:
        results_by_job[result.job_id].append(result)
    return [
        task_job_from_record(job, tuple(results_by_job[job.job_id]))
        for job in sorted(jobs, key=lambda item: (item.round_index, item.position))
    ]


def task_job_from_record(
    record: PostgresTaskJobRecord,
    results: tuple[PostgresTaskJobResultRecord, ...],
) -> TaskJob:
    return TaskJob(
        job_id=record.job_id,
        job_type=record.job_type,
        round_index=record.round_index,
        position=record.position,
        status=TaskJobStatus(record.status),
        reason=record.reason,
        input=record.input_json,
        started_at=record.started_at,
        finished_at=record.finished_at,
        error=error_text(record.error_json),
        metadata=metadata(record.metadata),
        results=[
            task_job_result_from_record(result)
            for result in sorted(results, key=lambda item: item.position)
        ],
    )


def task_job_result_from_record(record: PostgresTaskJobResultRecord) -> TaskJobResult:
    return TaskJobResult(
        job_result_id=record.job_result_id,
        result_type=record.result_type,
        result=job_result_value(record.result_type, record.result_json),
        summary=record.summary_json,
        metadata=metadata(record.metadata),
    )


def task_final_result_from_record(task: PostgresTaskRecord) -> TaskFinalResult | None:
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


def host_actions_from_records(
    action_records: tuple[PostgresHostActionRecord, ...],
) -> list[HostAction]:
    actions: list[HostAction] = []
    for record in action_records:
        action_type = HostActionType(record.action_type)
        input_type = _INPUT_TYPE_BY_ACTION_TYPE[action_type]
        actions.append(
            HostAction(
                action_type=action_type,
                summary=record.summary,
                input=restore_domain_model_json(record.input_json, input_type),
                action_id=record.action_id,
                job_id=record.job_id,
                reason=record.reason,
                status=HostActionStatus(record.status),
                attempts=record.attempts,
                policy=restore_domain_model_json(record.policy_json, HostActionPolicy),
                metadata=metadata(record.metadata),
            )
        )
    return actions


def task_event_from_record(record: PostgresTaskEventRecord) -> TaskEvent:
    return TaskEvent(
        event_id=record.event_id,
        event_type=TaskEventType(record.event_type),
        message=record.message,
        data=metadata(record.data_json),
        job_id=record.job_id,
    )


def output_result_value(output_type: TaskOutputType, value: JsonObject) -> TaskOutputResult:
    result_type = _RESULT_TYPE_BY_OUTPUT_TYPE[output_type]
    return restore_domain_model_json(value, result_type)


def job_result_value(result_type: str, value: JsonObject) -> TaskOutputResult | JsonObject:
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


def _model_json(value: object) -> JsonObject:
    return cast(JsonObject, domain_model_json(value))


def _job_result_json(result: TaskJobResult) -> JsonObject:
    if isinstance(result.result, dict):
        return cast(JsonObject, dict(result.result))
    return _model_json(result.result)


def _action_id(action: HostAction, position: int, task_id: str) -> str:
    return action.action_id or stable_internal_id("host-action", task_id, position)
