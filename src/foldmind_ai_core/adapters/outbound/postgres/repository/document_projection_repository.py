from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.adapters.outbound.postgres.models.document_projections import (
    DocumentChunkRow,
)
from foldmind_ai_core.adapters.outbound.postgres.models.sources import (
    DocumentSourceRow,
)
from foldmind_ai_core.adapters.outbound.postgres.mappers.document_signal import (
    document_signal_row_from_domain,
    document_signal_texts_from_rows,
)
from foldmind_ai_core.adapters.outbound.postgres.mappers.indexing import (
    document_chunk_from_rows,
    document_chunk_row_from_domain,
    document_index_state_from_row,
    document_index_state_row_from_domain,
)
from foldmind_ai_core.adapters.outbound.postgres.policies.retention_policy import (
    PurgeAfterPolicy,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_chunk_store import (
    DocumentChunkStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_index_record_store import (
    DocumentIndexRecordStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_signal_store import (
    DocumentSignalStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_source_store import (
    DocumentSourceStore,
)
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.document_index_state import (
    DocumentIndexState,
)
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
)
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument


@dataclass(slots=True)
class DocumentProjectionRepository:
    document_sources: DocumentSourceStore
    document_index_records: DocumentIndexRecordStore
    document_chunks: DocumentChunkStore
    document_signals: DocumentSignalStore
    purge_after_policy: PurgeAfterPolicy = field(default_factory=PurgeAfterPolicy)

    async def has_current_document_index(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> bool:
        source_row = await self.document_sources.current_document_source_row(
            tenant=tenant,
            document_id=document_id,
        )
        if source_row is None:
            return False
        return await self.document_index_records.current_document_index_exists(
            document_id=document_id,
        )

    async def get_document_signal_texts(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        source_row = await self.document_sources.current_document_source_row(
            tenant=tenant,
            document_id=document_id,
        )
        if source_row is None:
            return ()
        rows = await self.document_signals.signal_text_rows_for_document(
            document_id=document_id,
        )
        return document_signal_texts_from_rows(rows)

    async def get_current_document_index_records(
        self,
        *,
        document_ids: tuple[str, ...],
    ) -> tuple[DocumentIndexState, ...]:
        rows = await self.document_index_records.current_document_index_record_rows(
            document_ids=document_ids,
        )
        return tuple(document_index_state_from_row(row) for row in rows)

    async def get_first_chunks_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
        limit: int,
    ) -> tuple[DocumentChunk, ...]:
        rows = await self.document_chunks.first_chunk_rows_for_documents(
            tenant=tenant,
            document_ids=document_ids,
            limit=limit,
        )
        return await self._document_chunks_from_rows(tenant=tenant, rows=tuple(rows))

    async def replace_document_projection(
        self,
        *,
        document: SourceDocument,
        chunks: tuple[DocumentChunk, ...],
        index_record: DocumentIndexState,
        signals: tuple[DocumentSignal, ...],
    ) -> None:
        await self.document_index_records.upsert_document_index_record(
            document_index_state_row_from_domain(index_record)
        )
        await self.document_chunks.replace_chunks_for_document(
            tenant=document.tenant,
            document_id=document.document_id,
            rows=tuple(document_chunk_row_from_domain(chunk) for chunk in chunks),
        )
        await self.document_signals.replace_signals_for_document(
            document_id=document.document_id,
            rows=tuple(document_signal_row_from_domain(signal) for signal in signals),
        )

    async def mark_document_projection_deleted(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        await self.document_signals.delete_signals_for_document(
            document_id=document_id,
        )
        await self.document_chunks.delete_chunks_for_document(
            tenant=tenant,
            document_id=document_id,
        )
        await self.document_index_records.mark_document_index_deleted(
            document_id=document_id,
            purge_after=self.purge_after_policy.purge_after(),
        )

    async def search_chunks_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        document_id: str | None,
        document_ids: tuple[str, ...],
    ) -> tuple[tuple[DocumentChunk, float], ...]:
        rows = await self.document_chunks.keyword_chunk_rows(
            tenant=tenant,
            query_text=query_text,
            top_k=top_k,
            document_id=document_id,
            document_ids=document_ids,
        )
        sources_by_document_id = await self._current_sources_by_document_id(
            tenant=tenant,
            document_ids=tuple(
                dict.fromkeys(chunk_row.document_id for chunk_row, _ in rows)
            ),
        )
        return tuple(
            (
                document_chunk_from_rows(
                    chunk_row=chunk_row,
                    source_row=source_row,
                ),
                score,
            )
            for chunk_row, score in rows
            if (source_row := sources_by_document_id.get(chunk_row.document_id))
            is not None
        )

    async def _document_chunks_from_rows(
        self,
        *,
        tenant: str,
        rows: tuple[DocumentChunkRow, ...],
    ) -> tuple[DocumentChunk, ...]:
        sources_by_document_id = await self._current_sources_by_document_id(
            tenant=tenant,
            document_ids=tuple(dict.fromkeys(row.document_id for row in rows)),
        )
        return tuple(
            document_chunk_from_rows(
                chunk_row=row,
                source_row=source_row,
            )
            for row in rows
            if (source_row := sources_by_document_id.get(row.document_id)) is not None
        )

    async def _current_sources_by_document_id(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, DocumentSourceRow]:
        source_rows = await self.document_sources.current_document_source_rows(
            tenant=tenant,
            document_ids=document_ids,
        )
        return {
            source_row.document_id: source_row
            for source_row in source_rows
        }
