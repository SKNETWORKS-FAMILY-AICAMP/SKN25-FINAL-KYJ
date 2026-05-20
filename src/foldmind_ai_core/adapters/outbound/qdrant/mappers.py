from __future__ import annotations

import math
from typing import Any, cast

from foldmind_ai_core.adapters.outbound.qdrant.models import (
    QdrantDocumentChunkPayload,
    QdrantDocumentPayload,
    QdrantFolderPayload,
    QdrantSignalPayload,
)
from foldmind_ai_core.core.application.projections.vector import (
    DocumentSignalVectorProjection,
    DocumentChunkVectorProjection,
    DocumentVectorProjection,
    FolderSignalVectorProjection,
    FolderVectorProjection,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.retrieval.results import (
    RetrievedDocument,
    RetrievedFolder,
    RetrievedSignal,
    RetrievedSignalEvidence,
)
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
            created_at=chunk.created_at,
            updated_at=chunk.updated_at,
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            text_hash=chunk.text_hash,
            chunk_index=chunk.chunk_index,
            chunking_version=chunk.chunking_version,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
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
            created_at=document.created_at,
            updated_at=document.updated_at,
            embedding_input_hash=document.embedding_input_hash,
            embedding_model=document.embedding_model,
            embedding_version=document.embedding_version,
            index_schema_version=document.index_schema_version,
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
            related_document_id=signal.related_document_id,
            attributes=dict(signal.attributes),
            evidence=tuple(dict(item) for item in signal.evidence),
            confidence=signal.confidence,
            embedding_input_hash=signal.embedding_input_hash,
            embedding_model=signal.embedding_model,
            embedding_version=signal.embedding_version,
            index_schema_version=signal.index_schema_version,
            metadata=dict(signal.metadata),
        )
    )


def folder_payload(folder: FolderVectorProjection) -> JsonObject:
    return folder_payload_to_json(
        QdrantFolderPayload(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            embedding_input_hash=folder.embedding_input_hash,
            embedding_model=folder.embedding_model,
            embedding_version=folder.embedding_version,
            index_schema_version=folder.index_schema_version,
        )
    )


def chunk_from_payload(payload: JsonObject) -> DocumentChunk:
    record = document_chunk_payload_from_json(payload)
    return DocumentChunk(
        tenant=record.tenant,
        document_type=record.document_type,
        document_id=record.document_id,
        source_version=record.source_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
        chunk_id=record.chunk_id,
        chunk_index=record.chunk_index,
        chunking_version=record.chunking_version,
        text=record.text,
        text_hash=record.text_hash,
        start_offset=record.start_offset,
        end_offset=record.end_offset,
        embedding_model=record.embedding_model,
        embedding_version=record.embedding_version,
        index_schema_version=record.index_schema_version,
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


def folder_from_payload(payload: JsonObject) -> RetrievedFolder:
    record = folder_payload_from_json(payload)
    return RetrievedFolder(
        tenant=record.tenant,
        folder_id=record.folder_id,
        source_version=record.source_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def document_chunk_payload_to_json(payload: QdrantDocumentChunkPayload) -> JsonObject:
    return {
        "kind": "document_chunk",
        "tenant": payload.tenant,
        "document_type": payload.document_type,
        "document_id": payload.document_id,
        "source_version": payload.source_version,
        "content_digest": payload.content_digest,
        "created_at": payload.created_at,
        "updated_at": payload.updated_at,
        "chunk_id": payload.chunk_id,
        "text": payload.text,
        "text_hash": payload.text_hash,
        "chunk_index": payload.chunk_index,
        "chunking_version": payload.chunking_version,
        "start_offset": payload.start_offset,
        "end_offset": payload.end_offset,
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
        "created_at": payload.created_at,
        "updated_at": payload.updated_at,
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
        "related_document_id": payload.related_document_id,
        "attributes": dict(payload.attributes),
        "evidence": list(payload.evidence),
        "confidence": payload.confidence,
        "embedding_input_hash": payload.embedding_input_hash,
        "embedding_model": payload.embedding_model,
        "embedding_version": payload.embedding_version,
        "index_schema_version": payload.index_schema_version,
        "metadata": dict(payload.metadata),
    }


def folder_payload_to_json(payload: QdrantFolderPayload) -> JsonObject:
    return {
        "kind": "folder",
        "tenant": payload.tenant,
        "folder_id": payload.folder_id,
        "source_version": payload.source_version,
        "created_at": payload.created_at,
        "updated_at": payload.updated_at,
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
        source_version=_optional_text(payload, "source_version"),
        content_digest=_optional_text(payload, "content_digest"),
        created_at=_required_text(payload, "created_at"),
        updated_at=_required_text(payload, "updated_at"),
        chunk_id=_required_text(payload, "chunk_id"),
        chunk_index=_required_int(payload, "chunk_index"),
        chunking_version=_optional_text(payload, "chunking_version"),
        text=_required_content_text(payload, "text"),
        text_hash=_optional_text(payload, "text_hash"),
        start_offset=_required_int(payload, "start_offset"),
        end_offset=_required_int(payload, "end_offset"),
        embedding_model=_optional_text(payload, "embedding_model"),
        embedding_version=_optional_text(payload, "embedding_version"),
        index_schema_version=_optional_text(payload, "index_schema_version"),
        metadata=_metadata_json(payload.get("metadata")),
    )


def document_payload_from_json(payload: JsonObject) -> QdrantDocumentPayload:
    return QdrantDocumentPayload(
        tenant=_required_text(payload, "tenant"),
        document_type=_optional_str(payload, "document_type"),
        document_id=_required_text(payload, "document_id"),
        source_version=_optional_text(payload, "source_version"),
        content_digest=_optional_text(payload, "content_digest"),
        created_at=_required_text(payload, "created_at"),
        updated_at=_required_text(payload, "updated_at"),
        embedding_input_hash=_optional_text(payload, "embedding_input_hash"),
        embedding_model=_optional_text(payload, "embedding_model"),
        embedding_version=_optional_text(payload, "embedding_version"),
        index_schema_version=_optional_text(payload, "index_schema_version"),
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
        source_version=_optional_text(payload, "source_version"),
        content_digest=_optional_str(payload, "content_digest"),
        related_document_id=_optional_str(payload, "related_document_id"),
        attributes=_metadata_json(payload.get("attributes")),
        evidence=tuple(
            _signal_evidence_payload(item, owner_kind=owner_kind)
            for item in _json_object_items(payload.get("evidence"), "evidence")
        ),
        confidence=_optional_confidence(payload, "confidence"),
        embedding_input_hash=_optional_text(payload, "embedding_input_hash"),
        embedding_model=_optional_text(payload, "embedding_model"),
        embedding_version=_optional_text(payload, "embedding_version"),
        index_schema_version=_optional_text(payload, "index_schema_version"),
        metadata=_metadata_json(payload.get("metadata")),
    )


def _retrieved_signal_evidence(payload: JsonObject) -> RetrievedSignalEvidence:
    return RetrievedSignalEvidence(
        chunk_id=_required_text(payload, "chunk_id"),
        quote=_required_content_text(payload, "quote"),
        start_offset=_optional_int(payload.get("start_offset"), "start_offset"),
        end_offset=_optional_int(payload.get("end_offset"), "end_offset"),
        metadata=_metadata_json(payload.get("metadata")),
    )


def _retrieved_signal_evidence_items(
    record: QdrantSignalPayload,
) -> tuple[RetrievedSignalEvidence, ...]:
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
        source_version=_optional_text(payload, "source_version"),
        created_at=_required_text(payload, "created_at"),
        updated_at=_required_text(payload, "updated_at"),
        embedding_input_hash=_optional_text(payload, "embedding_input_hash"),
        embedding_model=_optional_text(payload, "embedding_model"),
        embedding_version=_optional_text(payload, "embedding_version"),
        index_schema_version=_optional_text(payload, "index_schema_version"),
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


def _optional_text(payload: JsonObject, key: str) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    return value.strip()


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
