from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Double, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from foldmind_ai_core.adapters.outbound.postgres.models.base import (
    CreatedAndUpdatedAtColumns,
    PostgresOrmBase,
)


class FolderIndexRecordRow(CreatedAndUpdatedAtColumns, PostgresOrmBase):
    __tablename__ = "folder_index_records"

    folder_id: Mapped[str] = mapped_column(Text, primary_key=True)
    folder_index_input_digest: Mapped[str] = mapped_column(Text, nullable=False)
    folder_signal_input_digest: Mapped[str] = mapped_column(Text, nullable=False)
    signal_generation_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    folder_signal_refresh_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FolderSignalRow(CreatedAndUpdatedAtColumns, PostgresOrmBase):
    __tablename__ = "folder_signals"

    signal_id: Mapped[str] = mapped_column(Text, primary_key=True)
    folder_id: Mapped[str] = mapped_column(Text, nullable=False)
    folder_signal_input_digest: Mapped[str] = mapped_column(Text, nullable=False)
    signal_generation_version: Mapped[str] = mapped_column(Text, nullable=False)
    signal_type: Mapped[str] = mapped_column(Text, nullable=False)
    signal_key: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    related_document_id: Mapped[str | None] = mapped_column(Text)
    attributes_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )
    confidence: Mapped[float | None] = mapped_column(Double)
    extractor_name: Mapped[str] = mapped_column(Text, nullable=False)
    extractor_version: Mapped[str] = mapped_column(Text, nullable=False)
    generation_model: Mapped[str | None] = mapped_column(Text)
