from __future__ import annotations

from foldmind_ai_core.adapters.outbound.postgres.models.document_projections import (
    DocumentChunkRow,
    DocumentIndexRecordRow,
)
from foldmind_ai_core.adapters.outbound.postgres.models.folder_projections import (
    FolderIndexRecordRow,
)
from foldmind_ai_core.adapters.outbound.postgres.models.sources import (
    DocumentSourceRow,
    FolderSourceRow,
    SourceDocumentFolderRelationRow,
)
from foldmind_ai_core.core.domain.models.document_chunks import (
    DocumentChunk,
)
from foldmind_ai_core.core.domain.models.document_index_state import (
    DocumentIndexState,
)
from foldmind_ai_core.core.domain.models.folder_index_state import (
    FolderIndexState,
)
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)


def document_source_row_from_domain(document: SourceDocument) -> DocumentSourceRow:
    return DocumentSourceRow(
        document_id=document.document_id,
        tenant_id=document.tenant,
        document_type=document.document_type,
        source_version=document.source_version,
        source_created_at=document.created_at,
        source_updated_at=document.updated_at,
        title=document.title,
        content_digest=document.content_digest,
        content_size_bytes=document.content_size_bytes,
        metadata_json=dict(document.metadata),
    )


def document_index_state_row_from_domain(
    state: DocumentIndexState,
) -> DocumentIndexRecordRow:
    return DocumentIndexRecordRow(
        document_id=state.document_id,
        document_index_input_digest=state.document_index_input_digest,
        document_signal_input_digest=state.document_signal_input_digest,
        signal_generation_version=state.signal_generation_version,
    )


def document_index_state_from_row(
    row: DocumentIndexRecordRow,
) -> DocumentIndexState:
    return DocumentIndexState(
        document_id=row.document_id,
        document_index_input_digest=row.document_index_input_digest,
        document_signal_input_digest=row.document_signal_input_digest,
        signal_generation_version=row.signal_generation_version,
    )


def document_chunk_row_from_domain(chunk: DocumentChunk) -> DocumentChunkRow:
    return DocumentChunkRow(
        chunk_id=chunk.chunk_id,
        tenant_id=chunk.tenant,
        document_id=chunk.document_id,
        document_index_input_digest=chunk.document_index_input_digest,
        chunk_index=chunk.chunk_index,
        search_text=chunk.text,
        source_start_offset=chunk.start_offset,
        source_end_offset=chunk.end_offset,
    )


def document_chunk_from_rows(
    *,
    chunk_row: DocumentChunkRow,
    source_row: DocumentSourceRow,
) -> DocumentChunk:
    return DocumentChunk(
        tenant=source_row.tenant_id,
        document_type=source_row.document_type,
        document_id=source_row.document_id,
        source_version=source_row.source_version,
        document_index_input_digest=chunk_row.document_index_input_digest,
        created_at=_timestamp_text(source_row.source_created_at),
        updated_at=_timestamp_text(source_row.source_updated_at),
        chunk_id=chunk_row.chunk_id,
        chunk_index=chunk_row.chunk_index,
        text=chunk_row.search_text,
        start_offset=chunk_row.source_start_offset,
        end_offset=chunk_row.source_end_offset,
        metadata=dict(source_row.metadata_json),
    )


def source_document_folder_relation_rows_from_snapshot(
    snapshot: SourceDocumentFolderRelationSnapshot,
) -> tuple[SourceDocumentFolderRelationRow, ...]:
    return tuple(
        SourceDocumentFolderRelationRow(
            tenant_id=snapshot.tenant,
            document_id=snapshot.document_id,
            folder_id=folder_id,
        )
        for folder_id in _normalized_folder_ids(snapshot.folder_ids)
    )


def folder_source_row_from_domain(folder: SourceFolder) -> FolderSourceRow:
    return FolderSourceRow(
        folder_id=folder.folder_id,
        tenant_id=folder.tenant,
        source_version=folder.source_version,
        source_created_at=folder.created_at,
        source_updated_at=folder.updated_at,
        name=folder.name,
        path=folder.path,
        parent_folder_id=folder.parent_folder_id,
        description=folder.description,
        metadata_json=dict(folder.metadata),
    )


def source_folder_from_row(row: FolderSourceRow) -> SourceFolder:
    return SourceFolder(
        tenant=row.tenant_id,
        folder_id=row.folder_id,
        source_version=row.source_version,
        created_at=_timestamp_text(row.source_created_at),
        updated_at=_timestamp_text(row.source_updated_at),
        name=row.name,
        path=row.path,
        parent_folder_id=row.parent_folder_id,
        description=row.description,
        metadata=dict(row.metadata_json),
    )


def folder_index_state_row_from_domain(
    state: FolderIndexState,
) -> FolderIndexRecordRow:
    return FolderIndexRecordRow(
        folder_id=state.folder_id,
        folder_index_input_digest=state.folder_index_input_digest,
        folder_signal_input_digest=state.folder_signal_input_digest,
        signal_generation_version=state.signal_generation_version,
        folder_signal_refresh_status=str(state.folder_signal_refresh_status),
    )


def _normalized_folder_ids(folder_ids: tuple[str, ...]) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for folder_id in folder_ids:
        value = folder_id.strip()
        if not value or value in seen:
            continue
        values.append(value)
        seen.add(value)
    return tuple(values)


def _timestamp_text(value: object) -> str:
    if value is None:
        return ""
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    return str(value)
