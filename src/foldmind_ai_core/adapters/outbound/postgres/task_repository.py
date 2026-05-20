from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from foldmind_ai_core.adapters.outbound.postgres.client import (
    PostgresClient,
    jsonb,
    row_value,
)
from foldmind_ai_core.adapters.outbound.postgres.mappers.task import (
    host_action_records_from_snapshot,
    task_event_records_from_snapshot,
    task_input_records_from_snapshot,
    task_job_records_from_snapshot,
    task_job_result_records_from_snapshot,
    task_record_from_snapshot,
    task_snapshot_from_records,
)
from foldmind_ai_core.adapters.outbound.postgres.models.task import (
    PostgresHostActionRecord,
    PostgresTaskEventRecord,
    PostgresTaskInputRecord,
    PostgresTaskJobRecord,
    PostgresTaskJobResultRecord,
    PostgresTaskRecord,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskSnapshot
from foldmind_ai_core.shared.types import JsonObject

_UPSERT_TENANT_SCOPE_SQL = """
INSERT INTO tenant_storage_scopes (tenant_id, updated_at)
VALUES (%s, now())
ON CONFLICT (tenant_id)
DO UPDATE SET
    deleted_at = NULL,
    purge_after = NULL,
    updated_at = now()
"""

_UPSERT_TASK_SQL = """
INSERT INTO tasks (
    tenant,
    task_id,
    request_text,
    context_json,
    status,
    analysis_message,
    result_type,
    result_json,
    result_title,
    result_metadata,
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
    context_json = EXCLUDED.context_json,
    status = EXCLUDED.status,
    analysis_message = EXCLUDED.analysis_message,
    result_type = EXCLUDED.result_type,
    result_json = EXCLUDED.result_json,
    result_title = EXCLUDED.result_title,
    result_metadata = EXCLUDED.result_metadata,
    metadata = EXCLUDED.metadata,
    completed_at = CASE
        WHEN EXCLUDED.status IN ('completed', 'failed', 'rejected')
            THEN COALESCE(tasks.completed_at, EXCLUDED.completed_at)
        ELSE NULL
    END,
    updated_at = now()
"""

_GET_TASK_SQL = """
SELECT
    tenant,
    request_text,
    context_json,
    status,
    analysis_message,
    result_type,
    result_json,
    result_title,
    result_metadata,
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

_DELETE_TASK_INPUTS_SQL = """
DELETE FROM task_inputs
WHERE task_id = %s
"""

_INSERT_TASK_INPUT_SQL = """
INSERT INTO task_inputs (
    task_input_id,
    task_id,
    position,
    input_text,
    context_json,
    status,
    deleted_at
)
VALUES (
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    CASE WHEN %s = 'removed' THEN now() ELSE NULL END
)
"""

_GET_TASK_INPUTS_SQL = """
SELECT
    task_input_id,
    input_text,
    context_json,
    position,
    status
FROM task_inputs
WHERE task_id = %s
ORDER BY position ASC
"""

_DELETE_TASK_JOBS_SQL = """
DELETE FROM task_jobs
WHERE task_id = %s
"""

_INSERT_TASK_JOB_SQL = """
INSERT INTO task_jobs (
    job_id,
    task_id,
    round_index,
    position,
    job_type,
    status,
    reason,
    input_json,
    started_at,
    finished_at,
    error_json,
    metadata
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

_GET_TASK_JOBS_SQL = """
SELECT
    job_id,
    round_index,
    position,
    job_type,
    status,
    reason,
    input_json,
    started_at,
    finished_at,
    error_json,
    metadata
FROM task_jobs
WHERE task_id = %s
ORDER BY round_index ASC, position ASC
"""

_INSERT_TASK_JOB_RESULT_SQL = """
INSERT INTO task_job_results (
    job_result_id,
    job_id,
    position,
    result_type,
    result_json,
    summary_json,
    metadata
)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

_GET_TASK_JOB_RESULTS_SQL = """
SELECT
    job_result_id,
    job_id,
    position,
    result_type,
    result_json,
    summary_json,
    metadata
FROM task_job_results
WHERE job_id IN (
    SELECT job_id
    FROM task_jobs
    WHERE task_id = %s
)
ORDER BY job_id ASC, position ASC
"""

_DELETE_HOST_ACTIONS_SQL = """
DELETE FROM host_actions
WHERE task_id = %s
"""

_INSERT_HOST_ACTION_SQL = """
INSERT INTO host_actions (
    action_id,
    task_id,
    job_id,
    position,
    action_type,
    summary,
    reason,
    status,
    attempts,
    policy_json,
    input_json,
    metadata
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

_GET_HOST_ACTIONS_SQL = """
SELECT
    action_type,
    summary,
    input_json,
    action_id,
    job_id,
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

_UPSERT_TASK_EVENT_SQL = """
INSERT INTO task_events (
    task_id,
    job_id,
    event_id,
    event_type,
    message,
    data_json,
    created_at
)
VALUES (%s, %s, %s, %s, %s, %s, now())
ON CONFLICT (event_id)
DO UPDATE SET
    job_id = EXCLUDED.job_id,
    event_type = EXCLUDED.event_type,
    message = EXCLUDED.message,
    data_json = EXCLUDED.data_json
"""

_GET_TASK_ID_BY_INPUT_SQL = """
SELECT task_id
FROM task_inputs
WHERE task_input_id = %s
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
    job_id,
    data_json
FROM task_events
WHERE task_id = %s
ORDER BY created_at ASC, event_id ASC
"""


@dataclass(slots=True)
class PostgresTaskRepository:
    client: PostgresClient

    def create(self, snapshot: TaskSnapshot) -> None:
        self._save(snapshot)

    def get(self, *, task_id: str) -> TaskSnapshot | None:
        with self.client.connect() as conn:
            return self._get_with_connection(conn, task_id=task_id)

    def get_by_input_id(self, *, task_input_id: str) -> TaskSnapshot | None:
        with self.client.connect() as conn:
            row = conn.execute(
                _GET_TASK_ID_BY_INPUT_SQL,
                (task_input_id,),
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
        task = _task_record_from_row(task_id=task_id, row=row)
        return task_snapshot_from_records(
            task=task,
            inputs=_task_input_records_from_rows(
                task_id=task_id,
                rows=conn.execute(_GET_TASK_INPUTS_SQL, task_identity).fetchall(),
            ),
            jobs=_task_job_records_from_rows(
                task_id=task_id,
                rows=conn.execute(_GET_TASK_JOBS_SQL, task_identity).fetchall(),
            ),
            job_results=_task_job_result_records_from_rows(
                conn.execute(_GET_TASK_JOB_RESULTS_SQL, task_identity).fetchall()
            ),
            host_actions=_host_action_records_from_rows(
                conn.execute(_GET_HOST_ACTIONS_SQL, task_identity).fetchall()
            ),
            events=_task_event_records_from_rows(
                conn.execute(_GET_TASK_EVENTS_SQL, task_identity).fetchall()
            ),
        )

    def save(self, snapshot: TaskSnapshot) -> None:
        self._save(snapshot)

    def _save(self, snapshot: TaskSnapshot) -> None:
        task_identity = (snapshot.task_id,)
        task_record = task_record_from_snapshot(snapshot)
        with self.client.transaction() as conn:
            conn.execute(_UPSERT_TENANT_SCOPE_SQL, (task_record.tenant,))
            conn.execute(
                _UPSERT_TASK_SQL,
                (
                    task_record.tenant,
                    task_record.task_id,
                    task_record.request_text,
                    jsonb(task_record.context_json),
                    task_record.status,
                    task_record.analysis_message,
                    task_record.result_type,
                    jsonb(task_record.result_json)
                    if task_record.result_json is not None
                    else None,
                    task_record.result_title,
                    jsonb(task_record.result_metadata),
                    jsonb(task_record.metadata),
                    task_record.status,
                ),
            )
            _replace_inputs(
                conn,
                task_identity,
                task_input_records_from_snapshot(snapshot),
            )
            _replace_jobs(
                conn,
                task_identity,
                task_job_records_from_snapshot(snapshot),
                task_job_result_records_from_snapshot(snapshot),
            )
            conn.execute(_CLEAR_TASK_CURRENT_ACTION_SQL, task_identity)
            _replace_host_actions(
                conn,
                task_identity,
                host_action_records_from_snapshot(snapshot),
            )
            conn.execute(
                _UPDATE_TASK_RUNTIME_SQL,
                (
                    task_record.current_action_id,
                    jsonb(task_record.error_json)
                    if task_record.error_json is not None
                    else None,
                    task_record.task_id,
                ),
            )
            for event in task_event_records_from_snapshot(snapshot):
                _upsert_event(conn, task_id=snapshot.task_id, event=event)


def _replace_inputs(
    conn: Any,
    task_identity: tuple[str],
    inputs: tuple[PostgresTaskInputRecord, ...],
) -> None:
    conn.execute(_DELETE_TASK_INPUTS_SQL, task_identity)
    for task_input in inputs:
        conn.execute(
            _INSERT_TASK_INPUT_SQL,
            (
                task_input.task_input_id,
                task_input.task_id,
                task_input.position,
                task_input.input_text,
                jsonb(task_input.context_json),
                task_input.status,
                task_input.status,
            ),
        )


def _task_input_records_from_rows(
    *,
    task_id: str,
    rows: list[Any],
) -> tuple[PostgresTaskInputRecord, ...]:
    return tuple(
        PostgresTaskInputRecord(
            task_input_id=_str(row, "task_input_id", 0),
            task_id=task_id,
            input_text=_str(row, "input_text", 1),
            context_json=_json_object(row_value(row, "context_json", 2), "context_json"),
            position=_int(row, "position", 3),
            status=_str(row, "status", 4),
        )
        for row in rows
    )


def _replace_jobs(
    conn: Any,
    task_identity: tuple[str],
    jobs: tuple[PostgresTaskJobRecord, ...],
    job_results: tuple[PostgresTaskJobResultRecord, ...],
) -> None:
    conn.execute(_DELETE_TASK_JOBS_SQL, task_identity)
    for job in jobs:
        conn.execute(
            _INSERT_TASK_JOB_SQL,
            (
                job.job_id,
                job.task_id,
                job.round_index,
                job.position,
                job.job_type,
                job.status,
                job.reason,
                jsonb(job.input_json),
                job.started_at,
                job.finished_at,
                jsonb(job.error_json) if job.error_json is not None else None,
                jsonb(job.metadata),
            ),
        )
    for result in job_results:
        conn.execute(
            _INSERT_TASK_JOB_RESULT_SQL,
            (
                result.job_result_id,
                result.job_id,
                result.position,
                result.result_type,
                jsonb(result.result_json),
                jsonb(result.summary_json),
                jsonb(result.metadata),
            ),
        )


def _task_job_records_from_rows(
    *,
    task_id: str,
    rows: list[Any],
) -> tuple[PostgresTaskJobRecord, ...]:
    return tuple(
        PostgresTaskJobRecord(
            job_id=_str(row, "job_id", 0),
            task_id=task_id,
            round_index=_int(row, "round_index", 1),
            position=_int(row, "position", 2),
            job_type=_str(row, "job_type", 3),
            status=_str(row, "status", 4),
            reason=_str(row, "reason", 5),
            input_json=_json_object(row_value(row, "input_json", 6), "input_json"),
            started_at=_optional_str(row, "started_at", 7),
            finished_at=_optional_str(row, "finished_at", 8),
            error_json=_optional_json_object(row_value(row, "error_json", 9), "error_json"),
            metadata=_metadata_json_object(row_value(row, "metadata", 10)),
        )
        for row in rows
    )


def _task_job_result_records_from_rows(
    rows: list[Any],
) -> tuple[PostgresTaskJobResultRecord, ...]:
    return tuple(
        PostgresTaskJobResultRecord(
            job_result_id=_str(row, "job_result_id", 0),
            job_id=_str(row, "job_id", 1),
            position=_int(row, "position", 2),
            result_type=_str(row, "result_type", 3),
            result_json=_json_object(row_value(row, "result_json", 4), "result_json"),
            summary_json=_json_object(row_value(row, "summary_json", 5), "summary_json"),
            metadata=_metadata_json_object(row_value(row, "metadata", 6)),
        )
        for row in rows
    )


def _replace_host_actions(
    conn: Any,
    task_identity: tuple[str],
    actions: tuple[PostgresHostActionRecord, ...],
) -> None:
    conn.execute(_DELETE_HOST_ACTIONS_SQL, task_identity)
    for position, action in enumerate(actions):
        conn.execute(
            _INSERT_HOST_ACTION_SQL,
            (
                action.action_id,
                *task_identity,
                action.job_id,
                position,
                action.action_type,
                action.summary,
                action.reason,
                action.status,
                action.attempts,
                jsonb(action.policy_json),
                jsonb(action.input_json),
                jsonb(action.metadata),
            ),
        )


def _host_action_records_from_rows(
    rows: list[Any],
) -> tuple[PostgresHostActionRecord, ...]:
    return tuple(
        PostgresHostActionRecord(
            action_type=_str(row, "action_type", 0),
            summary=_str(row, "summary", 1),
            input_json=_json_object(row_value(row, "input_json", 2), "input_json"),
            action_id=_str(row, "action_id", 3),
            job_id=_optional_str(row, "job_id", 4),
            reason=_str(row, "reason", 5),
            status=_str(row, "status", 6),
            attempts=_int(row, "attempts", 7),
            policy_json=_json_object(row_value(row, "policy_json", 8), "policy_json"),
            metadata=_metadata_json_object(row_value(row, "metadata", 9)),
        )
        for row in rows
    )


def _upsert_event(
    conn: Any,
    *,
    task_id: str,
    event: PostgresTaskEventRecord,
) -> None:
    conn.execute(
        _UPSERT_TASK_EVENT_SQL,
        (
            task_id,
            event.job_id,
            event.event_id,
            event.event_type,
            event.message,
            jsonb(event.data_json),
        ),
    )


def _task_event_records_from_rows(
    rows: list[Any],
) -> tuple[PostgresTaskEventRecord, ...]:
    return tuple(
        PostgresTaskEventRecord(
            event_id=_str(row, "event_id", 0),
            event_type=_str(row, "event_type", 1),
            message=_str(row, "message", 2),
            job_id=_optional_str(row, "job_id", 3),
            data_json=_metadata_json_object(row_value(row, "data_json", 4)),
        )
        for row in rows
    )


def _task_record_from_row(*, task_id: str, row: Any) -> PostgresTaskRecord:
    return PostgresTaskRecord(
        task_id=task_id,
        tenant=_str(row, "tenant", 0),
        request_text=_str(row, "request_text", 1),
        context_json=_json_object(row_value(row, "context_json", 2), "context_json"),
        status=_str(row, "status", 3),
        analysis_message=_str(row, "analysis_message", 4),
        result_type=_optional_str(row, "result_type", 5),
        result_json=_optional_json_object(row_value(row, "result_json", 6), "result_json"),
        result_title=_optional_str(row, "result_title", 7),
        result_metadata=_metadata_json_object(row_value(row, "result_metadata", 8)),
        current_action_id=_optional_str(row, "current_action_id", 9),
        error_json=_optional_json_object(row_value(row, "error_json", 10), "error_json"),
        metadata=_metadata_json_object(row_value(row, "metadata", 11)),
    )


def _optional_json_object(value: object, key: str) -> JsonObject | None:
    if value is None:
        return None
    return _json_object(value, key)


def _json_object(value: object, key: str) -> JsonObject:
    if not isinstance(value, dict):
        raise ValueError(f"{key} must contain a JSON object.")
    return cast(JsonObject, value)


def _metadata_json_object(value: object) -> JsonObject:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("metadata fields must contain JSON objects.")
    return cast(JsonObject, value)


def _str(row: Any, key: str, index: int) -> str:
    value = row_value(row, key, index)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    return value


def _optional_str(row: Any, key: str, index: int) -> str | None:
    value = row_value(row, key, index)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    return value or None


def _int(row: Any, key: str, index: int) -> int:
    value = row_value(row, key, index)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer.")
    return value
