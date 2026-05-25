from __future__ import annotations

from foldmind_ai_core.core.application.models.vector_projection import (
    DocumentChunkVectorProjection,
    DocumentSignalVectorProjection,
    DocumentVectorProjection,
    FolderSignalVectorProjection,
    FolderVectorProjection,
    VectorWriteResult,
)
from foldmind_ai_core.core.domain.models.vector_projection_state import (
    VectorProjectionState,
)


def document_vector_projection_record(
    projection: DocumentVectorProjection,
    write: VectorWriteResult,
) -> VectorProjectionState:
    return _record(
        tenant=projection.tenant,
        source_kind="document",
        source_id=projection.document_id,
        vector_item_kind="document",
        vector_item_id=projection.document_id,
        source_input_digest=projection.source_input_digest,
        vector_input_digest=projection.vector_input_digest,
        write=write,
    )


def chunk_vector_projection_state(
    projections: tuple[DocumentChunkVectorProjection, ...],
    writes: tuple[VectorWriteResult, ...],
) -> tuple[VectorProjectionState, ...]:
    return tuple(
        _record(
            tenant=projection.tenant,
            source_kind="document",
            source_id=projection.document_id,
            vector_item_kind="chunk",
            vector_item_id=projection.chunk_id,
            source_input_digest=projection.source_input_digest,
            vector_input_digest=projection.vector_input_digest,
            write=write,
        )
        for projection, write in zip(projections, writes, strict=True)
    )


def document_signal_vector_projection_state(
    projections: tuple[DocumentSignalVectorProjection, ...],
    writes: tuple[VectorWriteResult, ...],
) -> tuple[VectorProjectionState, ...]:
    return tuple(
        _record(
            tenant=projection.tenant,
            source_kind="document",
            source_id=projection.document_id,
            vector_item_kind="signal",
            vector_item_id=projection.signal_id,
            source_input_digest=projection.source_input_digest,
            vector_input_digest=projection.vector_input_digest,
            write=write,
        )
        for projection, write in zip(projections, writes, strict=True)
    )


def folder_vector_projection_record(
    projection: FolderVectorProjection,
    write: VectorWriteResult,
) -> VectorProjectionState:
    return _record(
        tenant=projection.tenant,
        source_kind="folder",
        source_id=projection.folder_id,
        vector_item_kind="folder",
        vector_item_id=projection.folder_id,
        source_input_digest=projection.source_input_digest,
        vector_input_digest=projection.vector_input_digest,
        write=write,
    )


def folder_signal_vector_projection_state(
    projections: tuple[FolderSignalVectorProjection, ...],
    writes: tuple[VectorWriteResult, ...],
) -> tuple[VectorProjectionState, ...]:
    return tuple(
        _record(
            tenant=projection.tenant,
            source_kind="folder",
            source_id=projection.folder_id,
            vector_item_kind="signal",
            vector_item_id=projection.signal_id,
            source_input_digest=projection.source_input_digest,
            vector_input_digest=projection.vector_input_digest,
            write=write,
        )
        for projection, write in zip(projections, writes, strict=True)
    )


def _record(
    *,
    tenant: str,
    source_kind: str,
    source_id: str,
    vector_item_kind: str,
    vector_item_id: str,
    source_input_digest: str,
    vector_input_digest: str,
    write: VectorWriteResult,
) -> VectorProjectionState:
    return VectorProjectionState(
        tenant=tenant,
        collection_name=write.collection_name,
        point_id=write.point_id,
        source_kind=source_kind,
        source_id=source_id,
        vector_item_kind=vector_item_kind,
        vector_item_id=vector_item_id,
        source_input_digest=source_input_digest,
        vector_input_digest=vector_input_digest,
    )
