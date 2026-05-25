from __future__ import annotations

import hashlib

from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.application.models.indexing import FolderSignalInvalidation
from foldmind_ai_core.core.application.models.vector_projection import VectorProjectionSpec
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.outbox import (
    OutboxEvent,
    OutboxEventType,
    OutboxSourceKind,
)
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
    DocumentSignalEvidence,
)
from foldmind_ai_core.core.domain.models.folder_signals import FolderSignal
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.domain.services.document_indexing_invariant_service import (
    DocumentIndexingInvariantService,
)
from foldmind_ai_core.shared.input_digest import input_digest
from foldmind_ai_core.shared.source_versions import require_source_version
from foldmind_ai_core.shared.types import JsonObject
from foldmind_ai_core.shared.validation import InvalidInputError


def document_indexed_event(
    *,
    document: SourceDocument,
    chunks: tuple[DocumentChunk, ...],
    index_record: DocumentIndexState,
    signals: tuple[DocumentSignal, ...],
    vector_projection_spec: VectorProjectionSpec,
    chunking_version: str,
) -> OutboxEvent:
    DocumentIndexingInvariantService().validate_indexed_context(
        document=document,
        chunks=chunks,
        index_state=index_record,
        signals=signals,
    )
    content_digest = document.content_digest
    content_size_bytes = document.content_size_bytes
    payload: JsonObject = {
        "source_document": source_document_payload(
            document,
            content_digest=content_digest,
            content_size_bytes=content_size_bytes,
        ),
        "chunks": [
            document_chunk_payload(
                chunk,
                content_digest=content_digest,
                vector_projection_spec=vector_projection_spec,
                chunking_version=chunking_version,
            )
            for chunk in chunks
        ],
        "profile": document_index_record_payload(
            document=document,
            record=index_record,
            content_digest=content_digest,
        ),
        "signals": [
            document_signal_payload(signal, content_digest=content_digest)
            for signal in signals
        ],
    }
    return _outbox_event(
        tenant=document.tenant,
        source_kind=str(OutboxSourceKind.DOCUMENT),
        source_id=document.document_id,
        event_type=str(OutboxEventType.DOCUMENT_INDEXED),
        payload=payload,
    )


def document_deleted_event(
    *,
    tenant: str,
    document_id: str,
    source_version: str,
    affected_folder_ids: tuple[str, ...] = (),
) -> OutboxEvent:
    source_version = require_source_version(source_version, "source_version")
    return _outbox_event(
        tenant=tenant,
        source_kind=str(OutboxSourceKind.DOCUMENT),
        source_id=document_id,
        event_type=str(OutboxEventType.DOCUMENT_DELETED),
        idempotency_key=f"document-delete:{tenant}:{document_id}:{source_version}",
        payload={
            "tenant": tenant,
            "document_id": document_id,
            "affected_folder_ids": list(affected_folder_ids),
        },
    )


def document_folder_relations_indexed_event(
    snapshot: SourceDocumentFolderRelationSnapshot,
) -> OutboxEvent:
    return _outbox_event(
        tenant=snapshot.tenant,
        source_kind=str(OutboxSourceKind.DOCUMENT),
        source_id=snapshot.document_id,
        event_type=str(OutboxEventType.DOCUMENT_FOLDER_RELATIONS_INDEXED),
        payload={
            "folder_relation_snapshot": folder_relation_snapshot_payload(snapshot),
        },
    )


def folder_indexed_event(
    *,
    folder: SourceFolder,
) -> OutboxEvent:
    return _outbox_event(
        tenant=folder.tenant,
        source_kind=str(OutboxSourceKind.FOLDER),
        source_id=folder.folder_id,
        event_type=str(OutboxEventType.FOLDER_INDEXED),
        payload={
            "source_folder": source_folder_payload(folder),
        },
    )


def folder_signals_invalidated_event(
    invalidation: FolderSignalInvalidation,
) -> OutboxEvent:
    return _outbox_event(
        tenant=invalidation.tenant,
        source_kind=str(OutboxSourceKind.FOLDER),
        source_id=invalidation.folder_id,
        event_type=str(OutboxEventType.FOLDER_SIGNALS_INVALIDATED),
        payload={
            "tenant": invalidation.tenant,
            "folder_id": invalidation.folder_id,
            "folder_signal_input_digest": invalidation.folder_signal_input_digest,
            "signal_generation_version": invalidation.signal_generation_version,
        },
    )


def folder_signals_indexed_event(
    *,
    folder: SourceFolder,
    folder_signal_input_digest: str,
    signal_generation_version: str,
    signals: tuple[FolderSignal, ...],
) -> OutboxEvent:
    return _outbox_event(
        tenant=folder.tenant,
        source_kind=str(OutboxSourceKind.FOLDER),
        source_id=folder.folder_id,
        event_type=str(OutboxEventType.FOLDER_SIGNALS_INDEXED),
        payload={
            "source_folder": source_folder_payload(folder),
            "folder_signal_input_digest": folder_signal_input_digest,
            "signal_generation_version": signal_generation_version,
            "signals": [folder_signal_payload(signal) for signal in signals],
        },
    )


def folder_deleted_event(
    *,
    tenant: str,
    folder_id: str,
    source_version: str,
) -> OutboxEvent:
    source_version = require_source_version(source_version, "source_version")
    return _outbox_event(
        tenant=tenant,
        source_kind=str(OutboxSourceKind.FOLDER),
        source_id=folder_id,
        event_type=str(OutboxEventType.FOLDER_DELETED),
        idempotency_key=f"folder-delete:{tenant}:{folder_id}:{source_version}",
        payload={
            "tenant": tenant,
            "folder_id": folder_id,
        },
    )


def source_document_payload(
    document: SourceDocument,
    *,
    content_digest: str | None = None,
    content_size_bytes: int | None = None,
) -> JsonObject:
    return {
        "tenant": document.tenant,
        "document_type": document.document_type,
        "document_id": document.document_id,
        "source_version": document.source_version,
        "content_digest": content_digest or document.content_digest,
        "content_size_bytes": content_size_bytes
        if content_size_bytes is not None
        else document.content_size_bytes,
        "title": document.title,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "metadata": document.metadata,
    }


def folder_relation_snapshot_payload(
    snapshot: SourceDocumentFolderRelationSnapshot,
) -> JsonObject:
    return {
        "tenant": snapshot.tenant,
        "document_id": snapshot.document_id,
        "source_version": snapshot.source_version,
        "folder_ids": list(snapshot.folder_ids),
    }


def source_folder_payload(
    folder: SourceFolder,
) -> JsonObject:
    return {
        "tenant": folder.tenant,
        "folder_id": folder.folder_id,
        "source_version": folder.source_version,
        "name": folder.name,
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
        "path": folder.path,
        "parent_folder_id": folder.parent_folder_id,
        "description": folder.description,
        "metadata": folder.metadata,
    }


def document_chunk_payload(
    chunk: DocumentChunk,
    *,
    content_digest: str,
    vector_projection_spec: VectorProjectionSpec,
    chunking_version: str,
) -> JsonObject:
    chunking_version = _required_text(chunking_version, "chunking_version")
    return {
        "tenant": chunk.tenant,
        "document_type": chunk.document_type,
        "document_id": chunk.document_id,
        "source_version": chunk.source_version,
        "content_digest": content_digest,
        "document_index_input_digest": chunk.document_index_input_digest,
        "source_input_digest": chunk.document_index_input_digest,
        "vector_input_digest": _vector_input_digest(
            embedding_input=chunk.text,
            embedding_model=vector_projection_spec.embedding_model,
            embedding_version=vector_projection_spec.embedding_version,
            vector_schema_version=vector_projection_spec.index_schema_version,
        ),
        "created_at": chunk.created_at,
        "updated_at": chunk.updated_at,
        "chunk_id": chunk.chunk_id,
        "chunk_index": chunk.chunk_index,
        "chunking_version": chunking_version,
        "search_text": chunk.text,
        "source_start_offset": chunk.start_offset,
        "source_end_offset": chunk.end_offset,
        "embedding_model": vector_projection_spec.embedding_model,
        "embedding_version": vector_projection_spec.embedding_version,
        "index_schema_version": vector_projection_spec.index_schema_version,
        "metadata": chunk.metadata,
    }


def document_index_record_payload(
    *,
    document: SourceDocument,
    record: DocumentIndexState,
    content_digest: str,
) -> JsonObject:
    return {
        "tenant": document.tenant,
        "document_type": document.document_type,
        "document_id": record.document_id,
        "source_version": document.source_version,
        "content_digest": content_digest,
        "document_index_input_digest": record.document_index_input_digest,
        "document_signal_input_digest": record.document_signal_input_digest,
        "signal_generation_version": record.signal_generation_version,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "title": document.title.strip() or document.document_id,
        "metadata": {"source_metadata": dict(document.metadata)},
    }


def document_signal_payload(
    signal: DocumentSignal,
    *,
    content_digest: str,
) -> JsonObject:
    return {
        "signal_id": signal.signal_id,
        "tenant": signal.tenant,
        "document_type": signal.document_type,
        "document_id": signal.document_id,
        "source_version": signal.source_version,
        "content_digest": content_digest,
        "document_signal_input_digest": signal.document_signal_input_digest,
        "signal_generation_version": signal.signal_generation_version,
        "signal_type": str(signal.signal_type),
        "signal_key": signal.signal_key,
        "text": signal.text,
        "attributes": signal.attributes,
        "evidence": [
            signal_evidence_payload(evidence)
            for evidence in signal.evidence
        ],
        "confidence": signal.confidence,
        "extractor_name": signal.extractor_name,
        "extractor_version": signal.extractor_version,
        "generation_model": signal.generation_model,
        "metadata": signal.metadata,
    }


def folder_signal_payload(
    signal: FolderSignal,
) -> JsonObject:
    return {
        "signal_id": signal.signal_id,
        "tenant": signal.tenant,
        "folder_id": signal.folder_id,
        "source_version": signal.source_version,
        "folder_signal_input_digest": signal.folder_signal_input_digest,
        "signal_generation_version": signal.signal_generation_version,
        "signal_type": str(signal.signal_type),
        "signal_key": signal.signal_key,
        "text": signal.text,
        "related_document_id": signal.related_document_id,
        "attributes": signal.attributes,
        "evidence": [dict(item) for item in signal.evidence],
        "confidence": signal.confidence,
        "extractor_name": signal.extractor_name,
        "extractor_version": signal.extractor_version,
        "generation_model": signal.generation_model,
        "metadata": signal.metadata,
    }


def signal_evidence_payload(evidence: DocumentSignalEvidence) -> JsonObject:
    return {
        "chunk_id": evidence.chunk_id,
        "quote": evidence.quote,
        "start_offset": evidence.start_offset,
        "end_offset": evidence.end_offset,
        "metadata": evidence.metadata,
    }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError(f"{name} must not be blank.")
    return value.strip()


def _vector_input_digest(
    *,
    embedding_input: str,
    embedding_model: str,
    embedding_version: str,
    vector_schema_version: str,
) -> str:
    return input_digest(
        "vector",
        {
            "embedding_input_hash": _sha256(embedding_input),
            "embedding_model": embedding_model,
            "embedding_version": embedding_version,
            "vector_schema_version": vector_schema_version,
        },
    )


def _outbox_event(
    *,
    tenant: str,
    source_kind: str,
    source_id: str,
    event_type: str,
    payload: JsonObject,
    idempotency_key: str = "",
) -> OutboxEvent:
    event = OutboxEvent(
        tenant=tenant,
        source_kind=source_kind,
        source_id=source_id,
        event_type=event_type,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    return event
