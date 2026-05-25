from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Double, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from foldmind_ai_core.adapters.outbound.postgres.models.base import (
    CreatedAndUpdatedAtColumns,
    PostgresOrmBase,
)


class DocumentIndexRecordRow(CreatedAndUpdatedAtColumns, PostgresOrmBase):
    __tablename__ = "document_index_records"

    document_id: Mapped[str] = mapped_column(Text, primary_key=True)
    document_index_input_digest: Mapped[str] = mapped_column(Text, nullable=False)
    document_signal_input_digest: Mapped[str] = mapped_column(Text, nullable=False)
    signal_generation_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentChunkRow(CreatedAndUpdatedAtColumns, PostgresOrmBase):
    __tablename__ = "document_chunks"

    chunk_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[str] = mapped_column(Text, nullable=False)
    document_index_input_digest: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    source_end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)


class DocumentSignalRow(CreatedAndUpdatedAtColumns, PostgresOrmBase):
    __tablename__ = "document_signals"

    signal_id: Mapped[str] = mapped_column(Text, primary_key=True)
    document_id: Mapped[str] = mapped_column(Text, nullable=False)
    document_signal_input_digest: Mapped[str] = mapped_column(Text, nullable=False)
    signal_generation_version: Mapped[str] = mapped_column(Text, nullable=False)
    signal_type: Mapped[str] = mapped_column(Text, nullable=False)
    signal_key: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
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
