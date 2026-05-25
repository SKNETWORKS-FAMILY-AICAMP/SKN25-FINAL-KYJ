from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from foldmind_ai_core.adapters.outbound.postgres.models.base import (
    CreatedAndUpdatedAtColumns,
    CreatedAtColumn,
    PostgresOrmBase,
)


class TaskRow(CreatedAndUpdatedAtColumns, PostgresOrmBase):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    tenant: Mapped[str] = mapped_column(Text, nullable=False)
    request_text: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_message: Mapped[str] = mapped_column(Text, nullable=False)
    result_type: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result_title: Mapped[str | None] = mapped_column(Text)
    result_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    current_action_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TaskInputRow(CreatedAtColumn, PostgresOrmBase):
    __tablename__ = "task_inputs"

    task_input_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TaskJobRow(CreatedAtColumn, PostgresOrmBase):
    __tablename__ = "task_jobs"

    job_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    round_index: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    job_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    input_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class TaskJobResultRow(CreatedAtColumn, PostgresOrmBase):
    __tablename__ = "task_job_results"

    job_result_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    job_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    result_type: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class HostActionRow(CreatedAndUpdatedAtColumns, PostgresOrmBase):
    __tablename__ = "host_actions"

    action_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    job_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    input_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class TaskEventRow(CreatedAtColumn, PostgresOrmBase):
    __tablename__ = "task_events"

    event_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    job_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
