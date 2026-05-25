from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from foldmind_ai_core.adapters.outbound.postgres.models.base import (
    CreatedAndUpdatedAtColumns,
    PostgresOrmBase,
)


class TenantStorageScopeRow(CreatedAndUpdatedAtColumns, PostgresOrmBase):
    __tablename__ = "tenant_storage_scopes"

    tenant_id: Mapped[str] = mapped_column(Text, primary_key=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentSourceRow(CreatedAndUpdatedAtColumns, PostgresOrmBase):
    __tablename__ = "document_sources"

    document_id: Mapped[str] = mapped_column(Text, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str | None] = mapped_column(Text)
    source_version: Mapped[str] = mapped_column(Text, nullable=False)
    source_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    title_search_vector: Mapped[str | None] = mapped_column(TSVECTOR)
    content_digest: Mapped[str] = mapped_column(Text, nullable=False)
    content_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FolderSourceRow(CreatedAndUpdatedAtColumns, PostgresOrmBase):
    __tablename__ = "folder_sources"

    folder_id: Mapped[str] = mapped_column(Text, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_version: Mapped[str] = mapped_column(Text, nullable=False)
    source_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_search_vector: Mapped[str | None] = mapped_column(TSVECTOR)
    path: Mapped[str | None] = mapped_column(Text)
    parent_folder_id: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    description_search_vector: Mapped[str | None] = mapped_column(TSVECTOR)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceDocumentFolderRelationRow(CreatedAndUpdatedAtColumns, PostgresOrmBase):
    __tablename__ = "source_document_folder_relations"

    tenant_id: Mapped[str] = mapped_column(Text, primary_key=True)
    document_id: Mapped[str] = mapped_column(Text, primary_key=True)
    folder_id: Mapped[str] = mapped_column(Text, primary_key=True)
