from __future__ import annotations

from typing import Any

from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.reference.documents import (
    DocumentVectorProjection,
)
from foldmind_ai_core.domain.reference.folders import FolderVectorProjection
from foldmind_ai_core.domain.retrieval.results import RetrievedDocument, RetrievedFolder
from foldmind_ai_core.shared.types import Metadata


def payload_from_point(point: Any) -> dict[str, Any]:
    payload = getattr(point, "payload", None)
    return payload if isinstance(payload, dict) else {}


def chunk_payload(chunk: DocumentChunk) -> Metadata:
    return {
        "kind": "document_chunk",
        "tenant": chunk.tenant,
        "document_type": chunk.document_type,
        "document_id": chunk.document_id,
        "source_version": chunk.source_version,
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "text_hash": chunk.text_hash,
        "chunk_index": chunk.chunk_index,
        "chunking_version": chunk.chunking_version,
        "start_offset": chunk.start_offset,
        "end_offset": chunk.end_offset,
        "metadata": chunk.metadata,
        "embedding_model": chunk.embedding_model,
        "embedding_version": chunk.embedding_version,
        "index_schema_version": chunk.index_schema_version,
    }


def document_payload(document: DocumentVectorProjection) -> Metadata:
    return {
        "kind": "document",
        "tenant": document.tenant,
        "document_type": document.document_type,
        "document_id": document.document_id,
        "source_version": document.source_version,
        "profile_version": document.profile_version,
        "profile_schema_version": document.profile_schema_version,
        "concept_ids": list(document.concept_ids),
        "profile_confidence": document.profile_confidence,
        "embedding_input_hash": document.embedding_input_hash,
        "embedding_model": document.embedding_model,
        "embedding_version": document.embedding_version,
        "index_schema_version": document.index_schema_version,
    }


def folder_payload(folder: FolderVectorProjection) -> Metadata:
    return {
        "kind": "folder",
        "tenant": folder.tenant,
        "folder_id": folder.folder_id,
        "source_version": folder.source_version,
        "embedding_model": folder.embedding_model,
        "embedding_version": folder.embedding_version,
        "index_schema_version": folder.index_schema_version,
        "embedding_input_hash": folder.embedding_input_hash,
    }


def chunk_from_payload(payload: dict[str, Any]) -> DocumentChunk:
    return DocumentChunk(
        tenant=str(payload["tenant"]),
        document_type=str(payload["document_type"]),
        document_id=str(payload["document_id"]),
        source_version=str(payload.get("source_version") or ""),
        chunk_id=str(payload["chunk_id"]),
        chunk_index=int(payload["chunk_index"]),
        chunking_version=str(payload.get("chunking_version") or ""),
        text=str(payload["text"]),
        text_hash=str(payload.get("text_hash") or ""),
        start_offset=int(payload["start_offset"]),
        end_offset=int(payload["end_offset"]),
        embedding_model=str(payload.get("embedding_model") or ""),
        embedding_version=str(payload.get("embedding_version") or ""),
        index_schema_version=str(payload.get("index_schema_version") or ""),
        metadata=dict(payload.get("metadata") or {}),
    )


def document_from_payload(payload: dict[str, Any]) -> RetrievedDocument:
    return RetrievedDocument(
        tenant=str(payload["tenant"]),
        document_type=str(payload["document_type"]),
        document_id=str(payload["document_id"]),
        source_version=str(payload.get("source_version") or ""),
        profile_version=_optional_str(payload, "profile_version"),
        profile_schema_version=str(payload["profile_schema_version"]),
        concept_ids=_payload_string_tuple(payload, "concept_ids"),
        profile_confidence=_optional_float(payload, "profile_confidence"),
    )


def folder_from_payload(payload: dict[str, Any]) -> RetrievedFolder:
    return RetrievedFolder(
        tenant=str(payload["tenant"]),
        folder_id=str(payload["folder_id"]),
        source_version=str(payload.get("source_version") or ""),
    )


def _optional_str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return str(value) if value is not None else None


def _optional_float(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    return float(value) if value is not None else None


def _payload_string_tuple(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    return tuple(str(item) for item in payload.get(key, ()))
