from __future__ import annotations

import math
from typing import Any, cast

from foldmind_ai_core.adapters.outbound.qdrant.models import (
    QdrantDocumentChunkPayload,
    QdrantDocumentPayload,
    QdrantFolderPayload,
    QdrantSignalPayload,
)
from foldmind_ai_core.core.application.models.vector_projection import (
    DocumentChunkVectorProjection,
    DocumentSignalVectorProjection,
    DocumentVectorProjection,
    FolderSignalVectorProjection,
    FolderVectorProjection,
)
from foldmind_ai_core.core.application.models.retrieval import (
    RetrievedDocument,
    RetrievedSignal,
)
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.document_signals import DocumentSignalEvidence
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.shared.types import JsonObject


def payload_from_point(point: Any) -> JsonObject:
    payload = getattr(point, "payload", None)
    return cast(JsonObject, payload if isinstance(payload, dict) else {})


def score_from_point(point: Any) -> float | None:
    value = getattr(point, "score", 0.0)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    score = float(value)
    return score if math.isfinite(score) else None


def chunk_payload(chunk: DocumentChunkVectorProjection) -> JsonObject:
    return document_chunk_payload_to_json(
        QdrantDocumentChunkPayload(
            tenant=chunk.tenant,
            document_type=chunk.document_type,
            document_id=chunk.document_id,
            source_version=chunk.source_version,
            content_digest=chunk.content_digest,
            source_input_digest=chunk.source_input_digest,
            vector_input_digest=chunk.vector_input_digest,
            created_at=chunk.created_at,
            updated_at=chunk.updated_at,
            chunk_id=chunk.chunk_id,
            search_text=chunk.text,
            chunk_index=chunk.chunk_index,
            source_start_offset=chunk.start_offset,
            source_end_offset=chunk.end_offset,
            embedding_model=chunk.embedding_model,
            embedding_version=chunk.embedding_version,
            index_schema_version=chunk.index_schema_version,
            metadata=dict(chunk.metadata),
        )
    )


def document_payload(document: DocumentVectorProjection) -> JsonObject:
    return document_payload_to_json(
        QdrantDocumentPayload(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
            content_digest=document.content_digest,
            source_input_digest=document.source_input_digest,
            vector_input_digest=document.vector_input_digest,
            created_at=document.created_at,
            updated_at=document.updated_at,
            embedding_input_hash=document.embedding_input_hash,
            embedding_model=document.embedding_model,
            embedding_version=document.embedding_version,
            index_schema_version=document.index_schema_version,
            title=document.title,
            metadata=dict(document.metadata),
        )
    )


def signal_payload(
    signal: DocumentSignalVectorProjection | FolderSignalVectorProjection,
) -> JsonObject:
    if isinstance(signal, DocumentSignalVectorProjection):
        return _document_signal_payload(signal)
    return _folder_signal_payload(signal)


def _document_signal_payload(signal: DocumentSignalVectorProjection) -> JsonObject:
    return signal_payload_to_json(
        QdrantSignalPayload(
            signal_id=signal.signal_id,
            tenant=signal.tenant,
            owner_kind="document",
            document_type=signal.document_type,
            document_id=signal.document_id,
            folder_id=None,
            signal_type=signal.signal_type,
            signal_key=signal.signal_key,
            text=signal.embedding_input,
            source_version=signal.source_version,
            content_digest=signal.content_digest,
            source_input_digest=signal.source_input_digest,
            vector_input_digest=signal.vector_input_digest,
            signal_generation_version=signal.signal_generation_version,
            related_document_id=None,
            attributes=dict(signal.attributes),
            evidence=tuple(
                {
                    "chunk_id": evidence.chunk_id,
                    "quote": evidence.quote,
                    "start_offset": evidence.start_offset,
                    "end_offset": evidence.end_offset,
                    "metadata": dict(evidence.metadata),
                }
                for evidence in signal.evidence
            ),
            confidence=signal.confidence,
            embedding_input_hash=signal.embedding_input_hash,
            embedding_model=signal.embedding_model,
            embedding_version=signal.embedding_version,
            index_schema_version=signal.index_schema_version,
            extractor_name=signal.extractor_name,
            extractor_version=signal.extractor_version,
            generation_model=signal.generation_model,
            metadata=dict(signal.metadata),
        )
    )


def _folder_signal_payload(signal: FolderSignalVectorProjection) -> JsonObject:
    return signal_payload_to_json(
        QdrantSignalPayload(
            signal_id=signal.signal_id,
            tenant=signal.tenant,
            owner_kind="folder",
            document_type=None,
            document_id=None,
            folder_id=signal.folder_id,
            signal_type=signal.signal_type,
            signal_key=signal.signal_key,
            text=signal.embedding_input,
            source_version=signal.source_version,
            content_digest=None,
            source_input_digest=signal.source_input_digest,
            vector_input_digest=signal.vector_input_digest,
            signal_generation_version=signal.signal_generation_version,
            related_document_id=signal.related_document_id,
            attributes=dict(signal.attributes),
            evidence=tuple(dict(item) for item in signal.evidence),
            confidence=signal.confidence,
            embedding_input_hash=signal.embedding_input_hash,
            embedding_model=signal.embedding_model,
            embedding_version=signal.embedding_version,
            index_schema_version=signal.index_schema_version,
            extractor_name=signal.extractor_name,
            extractor_version=signal.extractor_version,
            generation_model=signal.generation_model,
            metadata=dict(signal.metadata),
        )
    )


def folder_payload(folder: FolderVectorProjection) -> JsonObject:
    return folder_payload_to_json(
        QdrantFolderPayload(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
            source_input_digest=folder.source_input_digest,
            vector_input_digest=folder.vector_input_digest,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            embedding_input_hash=folder.embedding_input_hash,
            embedding_model=folder.embedding_model,
            embedding_version=folder.embedding_version,
            index_schema_version=folder.index_schema_version,
            name=folder.name,
            path=folder.path,
            parent_folder_id=folder.parent_folder_id,
            description=folder.description,
            metadata=dict(folder.metadata),
        )
    )


def chunk_from_payload(payload: JsonObject) -> DocumentChunk:
    record = document_chunk_payload_from_json(payload)
    return DocumentChunk(
        tenant=record.tenant,
        document_type=record.document_type,
        document_id=record.document_id,
        source_version=record.source_version,
        document_index_input_digest=record.source_input_digest,
        created_at=record.created_at,
        updated_at=record.updated_at,
        chunk_id=record.chunk_id,
        chunk_index=record.chunk_index,
        text=record.search_text,
        start_offset=record.source_start_offset,
        end_offset=record.source_end_offset,
        metadata=dict(record.metadata),
    )


def document_from_payload(payload: JsonObject) -> RetrievedDocument:
    record = document_payload_from_json(payload)
    return RetrievedDocument(
        tenant=record.tenant,
        document_type=record.document_type,
        document_id=record.document_id,
        source_version=record.source_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
        snippet=record.title,
        metadata=dict(record.metadata),
    )


def signal_from_payload(payload: JsonObject) -> RetrievedSignal:
    record = signal_payload_from_json(payload)
    return RetrievedSignal(
        signal_id=record.signal_id,
        tenant=record.tenant,
        document_type=record.document_type,
        owner_kind=record.owner_kind,
        signal_type=record.signal_type,
        signal_key=record.signal_key,
        text=record.text,
        document_id=record.document_id,
        folder_id=record.folder_id,
        related_document_id=record.related_document_id,
        source_version=record.source_version,
        evidence=tuple(_retrieved_signal_evidence_items(record)),
        confidence=record.confidence,
        metadata=dict(record.metadata),
    )


def folder_from_payload(payload: JsonObject) -> SourceFolder:
    record = folder_payload_from_json(payload)
    return SourceFolder(
        tenant=record.tenant,
        folder_id=record.folder_id,
        source_version=record.source_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
        name=record.name,
        path=record.path,
        parent_folder_id=record.parent_folder_id,
        description=record.description,
        metadata=dict(record.metadata),
    )


def document_chunk_payload_to_json(payload: QdrantDocumentChunkPayload) -> JsonObject:
    return {
        "kind": "document_chunk",
        "tenant": payload.tenant,
        "document_type": payload.document_type,
        "document_id": payload.document_id,
        "source_version": payload.source_version,
        "content_digest": payload.content_digest,
        "source_input_digest": payload.source_input_digest,
        "vector_input_digest": payload.vector_input_digest,
        "created_at": payload.created_at,
        "updated_at": payload.updated_at,
        "chunk_id": payload.chunk_id,
        "search_text": payload.search_text,
        "chunk_index": payload.chunk_index,
        "source_start_offset": payload.source_start_offset,
        "source_end_offset": payload.source_end_offset,
        "metadata": dict(payload.metadata),
        "embedding_model": payload.embedding_model,
        "embedding_version": payload.embedding_version,
        "index_schema_version": payload.index_schema_version,
    }


def document_payload_to_json(payload: QdrantDocumentPayload) -> JsonObject:
    return {
        "kind": "document",
        "tenant": payload.tenant,
        "document_type": payload.document_type,
        "document_id": payload.document_id,
        "source_version": payload.source_version,
        "content_digest": payload.content_digest,
        "source_input_digest": payload.source_input_digest,
        "vector_input_digest": payload.vector_input_digest,
        "created_at": payload.created_at,
        "updated_at": payload.updated_at,
        "title": payload.title,
        "metadata": dict(payload.metadata),
        "embedding_input_hash": payload.embedding_input_hash,
        "embedding_model": payload.embedding_model,
        "embedding_version": payload.embedding_version,
        "index_schema_version": payload.index_schema_version,
    }


def signal_payload_to_json(payload: QdrantSignalPayload) -> JsonObject:
    return {
        "kind": "signal",
        "signal_id": payload.signal_id,
        "tenant": payload.tenant,
        "owner_kind": payload.owner_kind,
        "document_type": payload.document_type,
        "document_id": payload.document_id,
        "folder_id": payload.folder_id,
        "signal_type": payload.signal_type,
        "signal_key": payload.signal_key,
        "text": payload.text,
        "source_version": payload.source_version,
        "content_digest": payload.content_digest,
        "source_input_digest": payload.source_input_digest,
        "vector_input_digest": payload.vector_input_digest,
        "signal_generation_version": payload.signal_generation_version,
        "related_document_id": payload.related_document_id,
        "attributes": dict(payload.attributes),
        "evidence": list(payload.evidence),
        "confidence": payload.confidence,
        "embedding_input_hash": payload.embedding_input_hash,
        "embedding_model": payload.embedding_model,
        "embedding_version": payload.embedding_version,
        "index_schema_version": payload.index_schema_version,
        "extractor_name": payload.extractor_name,
        "extractor_version": payload.extractor_version,
        "generation_model": payload.generation_model,
        "metadata": dict(payload.metadata),
    }


def folder_payload_to_json(payload: QdrantFolderPayload) -> JsonObject:
    return {
        "kind": "folder",
        "tenant": payload.tenant,
        "folder_id": payload.folder_id,
        "source_version": payload.source_version,
        "source_input_digest": payload.source_input_digest,
        "vector_input_digest": payload.vector_input_digest,
        "created_at": payload.created_at,
        "updated_at": payload.updated_at,
        "name": payload.name,
        "path": payload.path,
        "parent_folder_id": payload.parent_folder_id,
        "description": payload.description,
        "metadata": dict(payload.metadata),
        "embedding_model": payload.embedding_model,
        "embedding_version": payload.embedding_version,
        "index_schema_version": payload.index_schema_version,
        "embedding_input_hash": payload.embedding_input_hash,
    }


def document_chunk_payload_from_json(
    payload: JsonObject,
) -> QdrantDocumentChunkPayload:
    return QdrantDocumentChunkPayload(
        tenant=_required_text(payload, "tenant"),
        document_type=_optional_str(payload, "document_type"),
        document_id=_required_text(payload, "document_id"),
        source_version=_required_text(payload, "source_version"),
        content_digest=_required_text(payload, "content_digest"),
        source_input_digest=_required_text(payload, "source_input_digest"),
        vector_input_digest=_required_text(payload, "vector_input_digest"),
        created_at=_required_text(payload, "created_at"),
        updated_at=_required_text(payload, "updated_at"),
        chunk_id=_required_text(payload, "chunk_id"),
        chunk_index=_required_int(payload, "chunk_index"),
        search_text=_required_content_text(payload, "search_text"),
        source_start_offset=_required_int(payload, "source_start_offset"),
        source_end_offset=_required_int(payload, "source_end_offset"),
        embedding_model=_required_text(payload, "embedding_model"),
        embedding_version=_required_text(payload, "embedding_version"),
        index_schema_version=_required_text(payload, "index_schema_version"),
        metadata=_metadata_json(payload.get("metadata")),
    )


def document_payload_from_json(payload: JsonObject) -> QdrantDocumentPayload:
    return QdrantDocumentPayload(
        tenant=_required_text(payload, "tenant"),
        document_type=_optional_str(payload, "document_type"),
        document_id=_required_text(payload, "document_id"),
        source_version=_required_text(payload, "source_version"),
        content_digest=_required_text(payload, "content_digest"),
        source_input_digest=_required_text(payload, "source_input_digest"),
        vector_input_digest=_required_text(payload, "vector_input_digest"),
        created_at=_required_text(payload, "created_at"),
        updated_at=_required_text(payload, "updated_at"),
        embedding_input_hash=_required_text(payload, "embedding_input_hash"),
        embedding_model=_required_text(payload, "embedding_model"),
        embedding_version=_required_text(payload, "embedding_version"),
        index_schema_version=_required_text(payload, "index_schema_version"),
        title=_optional_content_text(payload.get("title")) or "",
        metadata=_metadata_json(payload.get("metadata")),
    )


def signal_payload_from_json(payload: JsonObject) -> QdrantSignalPayload:
    owner_kind = _required_text(payload, "owner_kind")
    return QdrantSignalPayload(
        signal_id=_required_text(payload, "signal_id"),
        tenant=_required_text(payload, "tenant"),
        owner_kind=owner_kind,
        document_type=_optional_str(payload, "document_type"),
        document_id=_optional_str(payload, "document_id"),
        folder_id=_optional_str(payload, "folder_id"),
        signal_type=_required_text(payload, "signal_type"),
        signal_key=_required_text(payload, "signal_key"),
        text=_required_content_text(payload, "text"),
        source_version=_required_text(payload, "source_version"),
        content_digest=_optional_str(payload, "content_digest"),
        source_input_digest=_required_text(payload, "source_input_digest"),
        vector_input_digest=_required_text(payload, "vector_input_digest"),
        signal_generation_version=_required_text(payload, "signal_generation_version"),
        related_document_id=_optional_str(payload, "related_document_id"),
        attributes=_metadata_json(payload.get("attributes")),
        evidence=tuple(
            _signal_evidence_payload(item, owner_kind=owner_kind)
            for item in _json_object_items(payload.get("evidence"), "evidence")
        ),
        confidence=_optional_confidence(payload, "confidence"),
        embedding_input_hash=_required_text(payload, "embedding_input_hash"),
        embedding_model=_required_text(payload, "embedding_model"),
        embedding_version=_required_text(payload, "embedding_version"),
        index_schema_version=_required_text(payload, "index_schema_version"),
        extractor_name=_required_text(payload, "extractor_name"),
        extractor_version=_required_text(payload, "extractor_version"),
        generation_model=_optional_str(payload, "generation_model"),
        metadata=_metadata_json(payload.get("metadata")),
    )


def _retrieved_signal_evidence(payload: JsonObject) -> DocumentSignalEvidence:
    return DocumentSignalEvidence(
        chunk_id=_required_text(payload, "chunk_id"),
        quote=_required_content_text(payload, "quote"),
        start_offset=_optional_int(payload.get("start_offset"), "start_offset"),
        end_offset=_optional_int(payload.get("end_offset"), "end_offset"),
        metadata=_metadata_json(payload.get("metadata")),
    )


def _retrieved_signal_evidence_items(
    record: QdrantSignalPayload,
) -> tuple[DocumentSignalEvidence, ...]:
    if record.owner_kind != "document":
        return ()
    return tuple(_retrieved_signal_evidence(item) for item in record.evidence)


def _signal_evidence_payload(value: JsonObject, *, owner_kind: str) -> JsonObject:
    if owner_kind == "folder":
        return dict(value)
    return {
        "chunk_id": _required_text(value, "chunk_id"),
        "quote": _required_content_text(value, "quote"),
        "start_offset": _optional_int(value.get("start_offset"), "start_offset"),
        "end_offset": _optional_int(value.get("end_offset"), "end_offset"),
        "metadata": _metadata_json(value.get("metadata")),
    }


def folder_payload_from_json(payload: JsonObject) -> QdrantFolderPayload:
    return QdrantFolderPayload(
        tenant=_required_text(payload, "tenant"),
        folder_id=_required_text(payload, "folder_id"),
        source_version=_required_text(payload, "source_version"),
        source_input_digest=_required_text(payload, "source_input_digest"),
        vector_input_digest=_required_text(payload, "vector_input_digest"),
        created_at=_required_text(payload, "created_at"),
        updated_at=_required_text(payload, "updated_at"),
        embedding_input_hash=_required_text(payload, "embedding_input_hash"),
        embedding_model=_required_text(payload, "embedding_model"),
        embedding_version=_required_text(payload, "embedding_version"),
        index_schema_version=_required_text(payload, "index_schema_version"),
        name=_optional_content_text(payload.get("name")) or "",
        path=_optional_content_text(payload.get("path")),
        parent_folder_id=_optional_str(payload, "parent_folder_id"),
        description=_optional_content_text(payload.get("description")) or "",
        metadata=_metadata_json(payload.get("metadata")),
    )


def _optional_str(payload: JsonObject, key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    stripped = value.strip()
    return stripped or None


def _optional_confidence(payload: JsonObject, key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{key} must be numeric.")
    confidence = float(value)
    if not math.isfinite(confidence) or confidence < 0.0 or confidence > 1.0:
        raise ValueError(f"{key} must be between 0 and 1.")
    return confidence


def _required_text(payload: JsonObject, key: str) -> str:
    value = payload[key]
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{key} must not be blank.")
    return stripped


def _required_content_text(payload: JsonObject, key: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string.")
    return value


def _optional_content_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("content text must be a string.")
    return value


def _required_int(payload: JsonObject, key: str) -> int:
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer.")
    return value


def _optional_int(value: object, key: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer.")
    return value


def _json_object_items(value: object, key: str) -> tuple[JsonObject, ...]:
    if value is None:
        return ()
    if not isinstance(value, list | tuple):
        raise ValueError(f"{key} must be a list.")
    items: list[JsonObject] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{key} must contain JSON objects.")
        items.append(cast(JsonObject, item))
    return tuple(items)


def _metadata_json(value: object) -> JsonObject:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("metadata must be an object.")
    return cast(JsonObject, value)
