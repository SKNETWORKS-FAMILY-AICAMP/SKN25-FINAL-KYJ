from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import JsonObject


@dataclass(frozen=True, slots=True)
class PostgresTaskRecord:
    task_id: str
    tenant: str
    request_text: str
    context_json: JsonObject
    status: str
    analysis_message: str
    result_type: str | None = None
    result_json: JsonObject | None = None
    result_title: str | None = None
    result_metadata: JsonObject = field(default_factory=dict)
    current_action_id: str | None = None
    error_json: JsonObject | None = None
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PostgresTaskInputRecord:
    task_input_id: str
    task_id: str
    input_text: str
    context_json: JsonObject
    position: int
    status: str


@dataclass(frozen=True, slots=True)
class PostgresTaskJobRecord:
    job_id: str
    task_id: str
    round_index: int
    position: int
    job_type: str
    status: str
    reason: str
    input_json: JsonObject
    started_at: str | None = None
    finished_at: str | None = None
    error_json: JsonObject | None = None
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PostgresTaskJobResultRecord:
    job_result_id: str
    job_id: str
    position: int
    result_type: str
    result_json: JsonObject
    summary_json: JsonObject
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PostgresHostActionRecord:
    action_id: str
    job_id: str | None
    action_type: str
    summary: str
    input_json: JsonObject
    reason: str
    status: str
    attempts: int
    policy_json: JsonObject
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PostgresTaskEventRecord:
    event_id: str
    event_type: str
    message: str
    job_id: str | None = None
    data_json: JsonObject = field(default_factory=dict)
