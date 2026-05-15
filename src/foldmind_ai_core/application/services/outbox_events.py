from __future__ import annotations

from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.indexing.outbox import (
    OutboxAggregateType,
    OutboxEvent,
    OutboxEventType,
)
from foldmind_ai_core.domain.profiling.models import DocumentProfile
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.reference.folders import SourceFolder
from foldmind_ai_core.shared.types import Metadata


def document_indexed_event(
    *,
    document: SourceDocument,
    chunks: tuple[DocumentChunk, ...],
    profile: DocumentProfile,
) -> OutboxEvent:
    return OutboxEvent(
        aggregate_type=str(OutboxAggregateType.DOCUMENT),
        aggregate_id=document.document_id,
        event_type=str(OutboxEventType.DOCUMENT_INDEXED),
        payload={
            "source_document": source_document_payload(document),
            "chunks": [document_chunk_payload(chunk) for chunk in chunks],
            "profile": document_profile_payload(profile),
        },
    )


def document_deleted_event(
    *,
    document_id: str,
) -> OutboxEvent:
    return OutboxEvent(
        aggregate_type=str(OutboxAggregateType.DOCUMENT),
        aggregate_id=document_id,
        event_type=str(OutboxEventType.DOCUMENT_DELETED),
        payload={
            "document_id": document_id,
        },
    )


def folder_indexed_event(*, folder: SourceFolder) -> OutboxEvent:
    return OutboxEvent(
        aggregate_type=str(OutboxAggregateType.FOLDER),
        aggregate_id=folder.folder_id,
        event_type=str(OutboxEventType.FOLDER_INDEXED),
        payload={
            "source_folder": source_folder_payload(folder),
        },
    )


def folder_deleted_event(
    *,
    folder_id: str,
) -> OutboxEvent:
    return OutboxEvent(
        aggregate_type=str(OutboxAggregateType.FOLDER),
        aggregate_id=folder_id,
        event_type=str(OutboxEventType.FOLDER_DELETED),
        payload={
            "folder_id": folder_id,
        },
    )


def source_document_payload(document: SourceDocument) -> Metadata:
    return {
        "tenant": document.tenant,
        "document_type": document.document_type,
        "document_id": document.document_id,
        "source_version": document.source_version,
        "title": document.title,
        "folder_ids": list(document.folder_ids),
        "tag_ids": list(document.tag_ids),
        "metadata": document.metadata,
    }


def source_folder_payload(folder: SourceFolder) -> Metadata:
    return {
        "tenant": folder.tenant,
        "folder_id": folder.folder_id,
        "source_version": folder.source_version,
        "name": folder.name,
        "path": folder.path,
        "parent_folder_id": folder.parent_folder_id,
        "description": folder.description,
        "metadata": folder.metadata,
    }


def document_chunk_payload(chunk: DocumentChunk) -> Metadata:
    return {
        "tenant": chunk.tenant,
        "document_type": chunk.document_type,
        "document_id": chunk.document_id,
        "source_version": chunk.source_version,
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


def document_profile_payload(profile: DocumentProfile) -> Metadata:
    return {
        "tenant": profile.tenant,
        "document_type": profile.document_type,
        "document_id": profile.document_id,
        "source_version": profile.source_version,
        "title": profile.title,
        "summary": profile.summary,
        "profile_version": profile.profile_version,
        "profile_schema_version": profile.profile_schema_version,
        "concepts": [
            {
                "concept_id": concept.concept_id,
                "concept_key": concept.concept_key,
                "label": concept.label,
                "confidence": concept.confidence,
                "evidence_chunk_ids": list(concept.evidence_chunk_ids),
                "metadata": concept.metadata,
            }
            for concept in profile.concepts
        ],
        "profile_confidence": profile.profile_confidence,
        "model": profile.model,
        "prompt_version": profile.prompt_version,
        "metadata": profile.metadata,
    }
