from __future__ import annotations

import hashlib

from foldmind_ai_core.core.application.models.vector_projection import (
    DocumentSignalVectorProjection,
    DocumentVectorProjection,
    FolderSignalVectorProjection,
    FolderVectorProjection,
)
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_signals import DocumentSignal
from foldmind_ai_core.core.domain.models.document_sources import DocumentSourceState
from foldmind_ai_core.core.domain.models.folder_signals import FolderSignal
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.shared.input_digest import input_digest

_FOLDER_SOURCE_PROJECTION_POLICY_VERSION = "1"


def document_vector_projection_from_index_record(
    document: DocumentSourceState,
    index_record: DocumentIndexState,
    signals: tuple[DocumentSignal, ...],
    *,
    embedding_model: str,
    embedding_version: str,
    index_schema_version: str,
) -> DocumentVectorProjection:
    embedding_input = _projection_text(
        (
            document.title,
            *(
                signal.text
                for signal in signals
                if signal.document_id == document.document_id
            ),
        )
    )
    return DocumentVectorProjection(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        content_digest=document.content_digest,
        source_input_digest=index_record.document_signal_input_digest,
        vector_input_digest=_vector_input_digest(
            embedding_input_hash=_content_hash(embedding_input),
            embedding_model=embedding_model,
            embedding_version=embedding_version,
            vector_schema_version=index_schema_version,
        ),
        created_at=document.created_at,
        updated_at=document.updated_at,
        embedding_input=embedding_input,
        embedding_input_hash=_content_hash(embedding_input),
        embedding_model=embedding_model,
        embedding_version=embedding_version,
        index_schema_version=index_schema_version,
        title=document.title,
        metadata=dict(document.metadata),
    )


def signal_vector_projection_from_signal(
    signal: DocumentSignal,
    *,
    content_digest: str,
    embedding_model: str,
    embedding_version: str,
    index_schema_version: str,
) -> DocumentSignalVectorProjection:
    return DocumentSignalVectorProjection(
        signal_id=signal.signal_id,
        tenant=signal.tenant,
        document_type=signal.document_type,
        document_id=signal.document_id,
        signal_type=str(signal.signal_type),
        signal_key=signal.signal_key,
        source_version=signal.source_version,
        content_digest=content_digest,
        source_input_digest=signal.document_signal_input_digest,
        vector_input_digest=_vector_input_digest(
            embedding_input_hash=_content_hash(signal.text),
            embedding_model=embedding_model,
            embedding_version=embedding_version,
            vector_schema_version=index_schema_version,
        ),
        signal_generation_version=signal.signal_generation_version,
        attributes=dict(signal.attributes),
        confidence=signal.confidence,
        evidence=signal.evidence,
        embedding_input=signal.text,
        embedding_input_hash=_content_hash(signal.text),
        embedding_model=embedding_model,
        embedding_version=embedding_version,
        index_schema_version=index_schema_version,
        extractor_name=signal.extractor_name,
        extractor_version=signal.extractor_version,
        generation_model=signal.generation_model,
        metadata=dict(signal.metadata),
    )


def folder_signal_vector_projection_from_signal(
    signal: FolderSignal,
    *,
    embedding_model: str,
    embedding_version: str,
    index_schema_version: str,
) -> FolderSignalVectorProjection:
    return FolderSignalVectorProjection(
        signal_id=signal.signal_id,
        tenant=signal.tenant,
        folder_id=signal.folder_id,
        signal_type=str(signal.signal_type),
        signal_key=signal.signal_key,
        source_version=signal.source_version,
        source_input_digest=signal.folder_signal_input_digest,
        vector_input_digest=_vector_input_digest(
            embedding_input_hash=_content_hash(signal.text),
            embedding_model=embedding_model,
            embedding_version=embedding_version,
            vector_schema_version=index_schema_version,
        ),
        signal_generation_version=signal.signal_generation_version,
        related_document_id=signal.related_document_id,
        attributes=dict(signal.attributes),
        confidence=signal.confidence,
        evidence=tuple(dict(item) for item in signal.evidence),
        embedding_input=signal.text,
        embedding_input_hash=_content_hash(signal.text),
        embedding_model=embedding_model,
        embedding_version=embedding_version,
        index_schema_version=index_schema_version,
        extractor_name=signal.extractor_name,
        extractor_version=signal.extractor_version,
        generation_model=signal.generation_model,
        metadata=dict(signal.metadata),
    )


def folder_vector_projection_from_source(
    folder: SourceFolder,
    *,
    embedding_model: str,
    embedding_version: str,
    index_schema_version: str,
) -> FolderVectorProjection:
    embedding_input = _projection_text((folder.name, folder.path or "", folder.description))
    return FolderVectorProjection(
        tenant=folder.tenant,
        folder_id=folder.folder_id,
        source_version=folder.source_version,
        source_input_digest=_folder_index_input_digest(folder),
        vector_input_digest=_vector_input_digest(
            embedding_input_hash=_content_hash(embedding_input),
            embedding_model=embedding_model,
            embedding_version=embedding_version,
            vector_schema_version=index_schema_version,
        ),
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        embedding_input=embedding_input,
        embedding_input_hash=_content_hash(embedding_input),
        embedding_model=embedding_model,
        embedding_version=embedding_version,
        index_schema_version=index_schema_version,
        name=folder.name,
        path=folder.path,
        parent_folder_id=folder.parent_folder_id,
        description=folder.description,
        metadata=dict(folder.metadata),
    )


def _projection_text(parts: tuple[str, ...]) -> str:
    return "\n\n".join(part.strip() for part in parts if part.strip())


def _content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _vector_input_digest(
    *,
    embedding_input_hash: str,
    embedding_model: str,
    embedding_version: str,
    vector_schema_version: str,
) -> str:
    return input_digest(
        "vector",
        {
            "embedding_input_hash": embedding_input_hash,
            "embedding_model": embedding_model,
            "embedding_version": embedding_version,
            "vector_schema_version": vector_schema_version,
        },
    )


def _folder_index_input_digest(folder: SourceFolder) -> str:
    return input_digest(
        "folder_index",
        {
            "folder_id": folder.folder_id,
            "name": folder.name,
            "path": folder.path,
            "parent_folder_id": folder.parent_folder_id,
            "description": folder.description,
            "metadata": dict(folder.metadata),
            "projection_policy_version": _FOLDER_SOURCE_PROJECTION_POLICY_VERSION,
        },
    )
