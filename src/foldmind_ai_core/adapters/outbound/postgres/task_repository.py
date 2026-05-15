from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from foldmind_ai_core.adapters.outbound.model_codec import (
    model_value,
    restore_model_value,
)
from foldmind_ai_core.adapters.outbound.postgres.client import (
    PostgresClient,
    jsonb,
    row_value,
)
from foldmind_ai_core.domain.generation.results import (
    AssistantClarification,
    DocumentRecommendationResult,
    DraftResult,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.domain.workflow.actions import (
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
from foldmind_ai_core.domain.workflow.tasks import (
    TaskAnalysis,
    TaskEvent,
    TaskEventType,
    TaskOutput,
    TaskOutputType,
    TaskRequestEntry,
    TaskRequestStatus,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.shared.internal_ids import stable_internal_id
from foldmind_ai_core.shared.types import Metadata

_UPSERT_TASK_SQL = """
INSERT INTO tasks (
    tenant,
    task_id,
    request_text,
    status,
    analysis_message,
    metadata,
    completed_at,
    updated_at
)
VALUES (
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    CASE WHEN %s IN ('completed', 'failed', 'rejected') THEN now() ELSE NULL END,
    now()
)
ON CONFLICT (task_id)
DO UPDATE SET
    tenant = EXCLUDED.tenant,
    request_text = EXCLUDED.request_text,
    status = EXCLUDED.status,
    analysis_message = EXCLUDED.analysis_message,
    metadata = EXCLUDED.metadata,
    completed_at = COALESCE(EXCLUDED.completed_at, tasks.completed_at),
    updated_at = now()
"""

_GET_TASK_SQL = """
SELECT
    tenant,
    request_text,
    status,
    analysis_message,
    current_action_id,
    error_json,
    metadata
FROM tasks
WHERE task_id = %s
"""

_UPDATE_TASK_RUNTIME_SQL = """
UPDATE tasks
SET
    current_action_id = %s,
    error_json = %s,
    updated_at = now()
WHERE task_id = %s
"""

_CLEAR_TASK_CURRENT_ACTION_SQL = """
UPDATE tasks
SET current_action_id = NULL
WHERE task_id = %s
"""

_DELETE_TASK_REQUESTS_SQL = """
DELETE FROM task_requests
WHERE task_id = %s
"""

_INSERT_TASK_REQUEST_SQL = """
INSERT INTO task_requests (
    task_request_id,
    task_id,
    position,
    request,
    status,
    removed_at
)
VALUES (
    %s,
    %s,
    %s,
    %s,
    %s,
    CASE WHEN %s = 'removed' THEN now() ELSE NULL END
)
"""

_GET_TASK_REQUESTS_SQL = """
SELECT
    task_request_id,
    request,
    position,
    status
FROM task_requests
WHERE task_id = %s
ORDER BY position ASC
"""

_DELETE_TASK_OUTPUTS_SQL = """
DELETE FROM task_outputs
WHERE task_id = %s
"""

_INSERT_TASK_OUTPUT_SQL = """
INSERT INTO task_outputs (
    output_id,
    task_id,
    position,
    output_type,
    title,
    result_json,
    metadata
)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

_GET_TASK_OUTPUTS_SQL = """
SELECT
    output_type,
    result_json,
    output_id,
    title,
    metadata
FROM task_outputs
WHERE task_id = %s
ORDER BY position ASC
"""

_DELETE_HOST_ACTION_DEPENDENCIES_SQL = """
DELETE FROM host_action_dependencies
WHERE task_id = %s
"""

_DELETE_HOST_ACTIONS_SQL = """
DELETE FROM host_actions
WHERE task_id = %s
"""

_INSERT_HOST_ACTION_SQL = """
INSERT INTO host_actions (
    action_id,
    task_id,
    position,
    action_type,
    summary,
    reason,
    status,
    attempts,
    policy_json,
    input_json,
    result_json,
    metadata
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s)
"""

_INSERT_HOST_ACTION_DEPENDENCY_SQL = """
INSERT INTO host_action_dependencies (
    task_id,
    action_id,
    depends_on_action_id
)
VALUES (%s, %s, %s)
ON CONFLICT (action_id, depends_on_action_id)
DO NOTHING
"""

_GET_HOST_ACTIONS_SQL = """
SELECT
    action_type,
    summary,
    input_json,
    action_id,
    reason,
    status,
    attempts,
    policy_json,
    metadata,
    position
FROM host_actions
WHERE task_id = %s
ORDER BY position ASC
"""

_GET_HOST_ACTION_DEPENDENCIES_SQL = """
SELECT action_id, depends_on_action_id
FROM host_action_dependencies
WHERE task_id = %s
ORDER BY action_id ASC, depends_on_action_id ASC
"""

_UPSERT_TASK_EVENT_SQL = """
INSERT INTO task_events (
    task_id,
    event_id,
    event_type,
    message,
    data_json,
    created_at
)
VALUES (%s, %s, %s, %s, %s, now())
ON CONFLICT (event_id)
DO UPDATE SET
    event_type = EXCLUDED.event_type,
    message = EXCLUDED.message,
    data_json = EXCLUDED.data_json
"""

_GET_TASK_ID_BY_REQUEST_SQL = """
SELECT task_id
FROM task_requests
WHERE task_request_id = %s
"""

_GET_TASK_ID_BY_ACTION_SQL = """
SELECT task_id
FROM host_actions
WHERE action_id = %s
"""

_GET_TASK_EVENTS_SQL = """
SELECT
    event_id,
    event_type,
    message,
    data_json
FROM task_events
WHERE task_id = %s
ORDER BY created_at ASC, event_id ASC
"""

_RESULT_TYPE_BY_OUTPUT_TYPE = {
    TaskOutputType.CLARIFICATION: AssistantClarification,
    TaskOutputType.DOCUMENT_RECOMMENDATION: DocumentRecommendationResult,
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


@dataclass(slots=True)
class PostgresTaskRepository:
    client: PostgresClient

    def create(self, snapshot: TaskSnapshot) -> None:
        self._save(snapshot)

    def get(self, *, task_id: str) -> TaskSnapshot | None:
        with self.client.connect() as conn:
            return self._get_with_connection(conn, task_id=task_id)

    def get_by_request_id(self, *, task_request_id: str) -> TaskSnapshot | None:
        with self.client.connect() as conn:
            row = conn.execute(
                _GET_TASK_ID_BY_REQUEST_SQL,
                (task_request_id,),
            ).fetchone()
            if row is None:
                return None
            return self._get_with_connection(conn, task_id=_str(row, "task_id", 0))

    def get_by_action_id(self, *, action_id: str) -> TaskSnapshot | None:
        with self.client.connect() as conn:
            row = conn.execute(_GET_TASK_ID_BY_ACTION_SQL, (action_id,)).fetchone()
            if row is None:
                return None
            return self._get_with_connection(conn, task_id=_str(row, "task_id", 0))

    def _get_with_connection(self, conn: Any, *, task_id: str) -> TaskSnapshot | None:
        task_identity = (task_id,)
        row = conn.execute(_GET_TASK_SQL, task_identity).fetchone()
        if row is None:
            return None
        requests = _requests_from_rows(
            task_id=task_id,
            rows=conn.execute(_GET_TASK_REQUESTS_SQL, task_identity).fetchall(),
        )
        outputs = _outputs_from_rows(
            conn.execute(_GET_TASK_OUTPUTS_SQL, task_identity).fetchall()
        )
        host_actions = _host_actions_from_rows(
            action_rows=conn.execute(_GET_HOST_ACTIONS_SQL, task_identity).fetchall(),
            dependency_rows=conn.execute(
                _GET_HOST_ACTION_DEPENDENCIES_SQL,
                task_identity,
            ).fetchall(),
        )
        events = _events_from_rows(
            conn.execute(_GET_TASK_EVENTS_SQL, task_identity).fetchall()
        )
        return TaskSnapshot(
            task_id=task_id,
            tenant=_str(row, "tenant", 0),
            request=_str(row, "request_text", 1),
            status=TaskStatus(_str(row, "status", 2)),
            analysis=TaskAnalysis(
                message=_str(row, "analysis_message", 3),
                outputs=outputs,
            ),
            requests=requests,
            host_actions=host_actions,
            error=_error_text(row_value(row, "error_json", 5)),
            current_action_id=_optional_str(row, "current_action_id", 4),
            events=events,
            metadata=_metadata(row_value(row, "metadata", 6)),
        )

    def save(self, snapshot: TaskSnapshot) -> None:
        self._save(snapshot)

    def _save(self, snapshot: TaskSnapshot) -> None:
        task_identity = (snapshot.task_id,)
        with self.client.connect() as conn:
            conn.execute(
                _UPSERT_TASK_SQL,
                (
                    snapshot.tenant,
                    snapshot.task_id,
                    snapshot.request,
                    str(snapshot.status),
                    snapshot.analysis.message,
                    jsonb(snapshot.metadata),
                    str(snapshot.status),
                ),
            )
            _replace_requests(conn, task_identity, snapshot.requests)
            _replace_outputs(conn, task_identity, snapshot.analysis.outputs)
            conn.execute(_CLEAR_TASK_CURRENT_ACTION_SQL, task_identity)
            _replace_host_actions(conn, task_identity, snapshot.host_actions)
            conn.execute(
                _UPDATE_TASK_RUNTIME_SQL,
                (
                    snapshot.current_action_id,
                    _nullable_jsonb(_error_json(snapshot.error)),
                    snapshot.task_id,
                ),
            )
            for event in snapshot.events:
                _upsert_event(
                    conn,
                    task_id=snapshot.task_id,
                    event=event,
                )


def _replace_requests(
    conn: Any,
    task_identity: tuple[str],
    requests: list[TaskRequestEntry],
) -> None:
    conn.execute(_DELETE_TASK_REQUESTS_SQL, task_identity)
    for request in sorted(requests, key=lambda item: item.position):
        conn.execute(
            _INSERT_TASK_REQUEST_SQL,
            (
                request.task_request_id,
                *task_identity,
                request.position,
                request.request,
                str(request.status),
                str(request.status),
            ),
        )


def _requests_from_rows(*, task_id: str, rows: list[Any]) -> list[TaskRequestEntry]:
    return [
        TaskRequestEntry(
            task_request_id=_str(row, "task_request_id", 0),
            task_id=task_id,
            request=_str(row, "request", 1),
            position=_int(row, "position", 2),
            status=TaskRequestStatus(_str(row, "status", 3)),
        )
        for row in rows
    ]


def _replace_outputs(
    conn: Any,
    task_identity: tuple[str],
    outputs: list[TaskOutput],
) -> None:
    conn.execute(_DELETE_TASK_OUTPUTS_SQL, task_identity)
    for position, output in enumerate(outputs):
        conn.execute(
            _INSERT_TASK_OUTPUT_SQL,
            (
                _output_id(output, position, task_identity[0]),
                *task_identity,
                position,
                str(output.output_type),
                output.title,
                jsonb(_model_json(output.result)),
                jsonb(output.metadata),
            ),
        )


def _outputs_from_rows(rows: list[Any]) -> list[TaskOutput]:
    outputs: list[TaskOutput] = []
    for row in rows:
        output_type = TaskOutputType(_str(row, "output_type", 0))
        result_type = _RESULT_TYPE_BY_OUTPUT_TYPE[output_type]
        outputs.append(
            TaskOutput(
                output_type=output_type,
                result=restore_model_value(row_value(row, "result_json", 1), result_type),
                output_id=_str(row, "output_id", 2),
                title=_optional_str(row, "title", 3),
                metadata=_metadata(row_value(row, "metadata", 4)),
            )
        )
    return outputs


def _replace_host_actions(
    conn: Any,
    task_identity: tuple[str],
    actions: list[HostAction],
) -> None:
    conn.execute(_DELETE_HOST_ACTION_DEPENDENCIES_SQL, task_identity)
    conn.execute(_DELETE_HOST_ACTIONS_SQL, task_identity)
    for position, action in enumerate(actions):
        action_id = _action_id(action, position, task_identity[0])
        conn.execute(
            _INSERT_HOST_ACTION_SQL,
            (
                action_id,
                *task_identity,
                position,
                str(action.action_type),
                action.summary,
                action.reason,
                str(action.status),
                action.attempts,
                jsonb(_model_json(action.policy)),
                jsonb(_model_json(action.input)),
                jsonb(cast(Metadata, action.metadata)),
            ),
        )
        for depends_on_action_id in action.depends_on:
            conn.execute(
                _INSERT_HOST_ACTION_DEPENDENCY_SQL,
                (*task_identity, action_id, depends_on_action_id),
            )


def _host_actions_from_rows(
    *,
    action_rows: list[Any],
    dependency_rows: list[Any],
) -> list[HostAction]:
    dependencies_by_action_id: dict[str, list[str]] = {}
    for row in dependency_rows:
        dependencies_by_action_id.setdefault(_str(row, "action_id", 0), []).append(
            _str(row, "depends_on_action_id", 1)
        )

    actions: list[HostAction] = []
    for row in action_rows:
        action_type = HostActionType(_str(row, "action_type", 0))
        input_type = _INPUT_TYPE_BY_ACTION_TYPE[action_type]
        action_id = _str(row, "action_id", 3)
        actions.append(
            HostAction(
                action_type=action_type,
                summary=_str(row, "summary", 1),
                input=restore_model_value(row_value(row, "input_json", 2), input_type),
                action_id=action_id,
                reason=_str(row, "reason", 4),
                status=HostActionStatus(_str(row, "status", 5)),
                attempts=_int(row, "attempts", 6),
                depends_on=dependencies_by_action_id.get(action_id, []),
                policy=restore_model_value(
                    row_value(row, "policy_json", 7),
                    HostActionPolicy,
                ),
                metadata=_metadata(row_value(row, "metadata", 8)),
            )
        )
    return actions


def _upsert_event(conn: Any, *, task_id: str, event: TaskEvent) -> None:
    conn.execute(
        _UPSERT_TASK_EVENT_SQL,
        (
            task_id,
            event.event_id,
            str(event.event_type),
            event.message,
            jsonb(cast(Metadata, event.data)),
        ),
    )


def _events_from_rows(rows: list[Any]) -> list[TaskEvent]:
    return [
        TaskEvent(
            event_id=_str(row, "event_id", 0),
            event_type=TaskEventType(_str(row, "event_type", 1)),
            message=_str(row, "message", 2),
            data=_metadata(row_value(row, "data_json", 3)),
        )
        for row in rows
    ]


def _model_json(value: object) -> Metadata:
    return cast(Metadata, model_value(value))


def _error_json(error: str | None) -> Metadata | None:
    return {"message": error} if error is not None else None


def _nullable_jsonb(value: Metadata | None) -> object | None:
    return jsonb(value) if value is not None else None


def _error_text(value: object) -> str | None:
    if isinstance(value, dict):
        message = value.get("message")
        if isinstance(message, str) and message:
            return message
    return None


def _output_id(output: TaskOutput, position: int, task_id: str) -> str:
    return output.output_id or stable_internal_id("task-output", task_id, position)


def _action_id(action: HostAction, position: int, task_id: str) -> str:
    return action.action_id or stable_internal_id("host-action", task_id, position)


def _metadata(value: object) -> Metadata:
    return cast(Metadata, value if isinstance(value, dict) else {})


def _str(row: Any, key: str, index: int) -> str:
    return str(row_value(row, key, index) or "")


def _optional_str(row: Any, key: str, index: int) -> str | None:
    value = row_value(row, key, index)
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _int(row: Any, key: str, index: int) -> int:
    return int(row_value(row, key, index))
