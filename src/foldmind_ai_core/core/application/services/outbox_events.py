from __future__ import annotations

import hashlib

from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.indexing.outbox import (
    OutboxEvent,
    OutboxEventType,
    OutboxSourceKind,
)
from foldmind_ai_core.core.domain.models.profiling import (
    DocumentSignal,
    DocumentProfile,
    FolderSignal,
    SignalEvidence,
)
from foldmind_ai_core.core.application.models.indexing import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.models.reference.folders import SourceFolder
from foldmind_ai_core.core.domain.services.indexing import validate_document_indexed_context
from foldmind_ai_core.shared.types import JsonObject


def document_indexed_event(
    *,
    document: SourceDocument,
    chunks: tuple[DocumentChunk, ...],
    profile: DocumentProfile,
    signals: tuple[DocumentSignal, ...],
) -> OutboxEvent:
    validate_document_indexed_context(
        document=document,
        chunks=chunks,
        profile=profile,
        signals=signals,
    )
    content_digest = _sha256(document.full_text)
    content_size_bytes = _utf8_size(document.full_text)
    payload: JsonObject = {
        "source_document": source_document_payload(
            document,
            content_digest=content_digest,
            content_size_bytes=content_size_bytes,
        ),
        "chunks": [
            document_chunk_payload(chunk, content_digest=content_digest)
            for chunk in chunks
        ],
        "profile": document_profile_payload(
            profile,
            content_digest=content_digest,
        ),
        "signals": [
            document_signal_payload(signal, content_digest=content_digest)
            for signal in signals
        ],
    }
    return OutboxEvent(
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
    affected_folder_ids: tuple[str, ...] = (),
) -> OutboxEvent:
    return OutboxEvent(
        tenant=tenant,
        source_kind=str(OutboxSourceKind.DOCUMENT),
        source_id=document_id,
        event_type=str(OutboxEventType.DOCUMENT_DELETED),
        idempotency_key=f"document-delete:{tenant}:{document_id}",
        payload={
            "tenant": tenant,
            "document_id": document_id,
            "affected_folder_ids": list(affected_folder_ids),
        },
    )


def document_folder_relations_indexed_event(
    snapshot: SourceDocumentFolderRelationSnapshot,
) -> OutboxEvent:
    return OutboxEvent(
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
    signals: tuple[FolderSignal, ...] = (),
) -> OutboxEvent:
    return OutboxEvent(
        tenant=folder.tenant,
        source_kind=str(OutboxSourceKind.FOLDER),
        source_id=folder.folder_id,
        event_type=str(OutboxEventType.FOLDER_INDEXED),
        payload={
            "source_folder": source_folder_payload(folder),
            "signals": [
                folder_signal_payload(signal)
                for signal in signals
            ],
        },
    )


def folder_deleted_event(
    *,
    tenant: str,
    folder_id: str,
) -> OutboxEvent:
    return OutboxEvent(
        tenant=tenant,
        source_kind=str(OutboxSourceKind.FOLDER),
        source_id=folder_id,
        event_type=str(OutboxEventType.FOLDER_DELETED),
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
    content_text = document.full_text
    return {
        "tenant": document.tenant,
        "document_type": document.document_type,
        "document_id": document.document_id,
        "source_version": document.source_version,
        "content_digest": content_digest or _sha256(content_text),
        "content_size_bytes": content_size_bytes
        if content_size_bytes is not None
        else _utf8_size(content_text),
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
) -> JsonObject:
    return {
        "tenant": chunk.tenant,
        "document_type": chunk.document_type,
        "document_id": chunk.document_id,
        "source_version": chunk.source_version,
        "content_digest": content_digest,
        "created_at": chunk.created_at,
        "updated_at": chunk.updated_at,
        "chunk_id": chunk.chunk_id,
        "chunk_index": chunk.chunk_index,
        "chunking_version": chunk.chunking_version,
        "text": chunk.text,
        "text_hash": chunk.text_hash,
        "start_offset": chunk.start_offset,
        "end_offset": chunk.end_offset,
        "embedding_model": chunk.embedding_model,
        "embedding_version": chunk.embedding_version,
        "index_schema_version": chunk.index_schema_version,
        "metadata": chunk.metadata,
    }


def document_profile_payload(
    profile: DocumentProfile,
    *,
    content_digest: str,
) -> JsonObject:
    return {
        "tenant": profile.tenant,
        "document_type": profile.document_type,
        "document_id": profile.document_id,
        "source_version": profile.source_version,
        "content_digest": content_digest,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "title": profile.title,
        "signal_set_version": profile.signal_set_version,
        "model": profile.model,
        "metadata": profile.metadata,
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
        "signal_type": str(signal.signal_type),
        "signal_key": signal.signal_key,
        "text": signal.text,
        "related_document_id": signal.related_document_id,
        "attributes": signal.attributes,
        "evidence": [dict(item) for item in signal.evidence],
        "confidence": signal.confidence,
        "extractor_name": signal.extractor_name,
        "extractor_version": signal.extractor_version,
        "metadata": signal.metadata,
    }


def signal_evidence_payload(evidence: SignalEvidence) -> JsonObject:
    return {
        "chunk_id": evidence.chunk_id,
        "quote": evidence.quote,
        "start_offset": evidence.start_offset,
        "end_offset": evidence.end_offset,
        "metadata": evidence.metadata,
    }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utf8_size(value: str) -> int:
    return len(value.encode("utf-8"))
