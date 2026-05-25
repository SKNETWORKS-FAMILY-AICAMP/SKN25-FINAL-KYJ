from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.domain.models.document_chunks import (
    DocumentChunk,
)
from foldmind_ai_core.core.domain.models.document_index_state import (
    DocumentIndexState,
)
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
)
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument

DocumentChunkKeywordMatch = tuple[DocumentChunk, float]


class DocumentProjectionRepositoryPort(Protocol):
    async def has_current_document_index(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> bool:
        ...

    async def get_document_signal_texts(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        ...

    async def get_current_document_index_records(
        self,
        *,
        document_ids: tuple[str, ...],
    ) -> tuple[DocumentIndexState, ...]:
        ...

    async def get_first_chunks_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
        limit: int,
    ) -> tuple[DocumentChunk, ...]:
        ...

    async def replace_document_projection(
        self,
        *,
        document: SourceDocument,
        chunks: tuple[DocumentChunk, ...],
        index_record: DocumentIndexState,
        signals: tuple[DocumentSignal, ...],
    ) -> None:
        ...

    async def mark_document_projection_deleted(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        ...

    async def search_chunks_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        document_id: str | None,
        document_ids: tuple[str, ...],
    ) -> tuple[DocumentChunkKeywordMatch, ...]:
        ...
