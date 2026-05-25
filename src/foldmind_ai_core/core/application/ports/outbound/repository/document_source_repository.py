from __future__ import annotations

from datetime import datetime
from typing import Protocol

from foldmind_ai_core.core.domain.models.document_sources import (
    DocumentSourceIdentity,
    DocumentSourceState,
    SourceDocument,
)
from foldmind_ai_core.shared.types import Metadata

DocumentSourceKeywordMatch = tuple[DocumentSourceState, float]


class DocumentSourceRepositoryPort(Protocol):
    async def upsert_document_source(
        self,
        document: SourceDocument,
    ) -> bool:
        ...

    async def get_current_document_source(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> DocumentSourceState | None:
        ...

    async def current_document_source_identity_for_update(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> DocumentSourceIdentity | None:
        ...

    async def get_current_document_sources(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> tuple[DocumentSourceState, ...]:
        ...

    async def document_identity_for_delete(
        self,
        document_id: str,
    ) -> DocumentSourceIdentity | None:
        ...

    async def mark_document_source_deleted(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        ...

    async def document_ids_for_scope(
        self,
        *,
        tenant: str,
        document_type: str | None,
        document_id: str | None,
        document_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
        metadata_filter: Metadata | None,
    ) -> tuple[str, ...]:
        ...

    async def search_titles_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        document_type: str | None,
        document_id: str | None,
        document_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
        metadata_filter: Metadata | None,
    ) -> tuple[DocumentSourceKeywordMatch, ...]:
        ...
