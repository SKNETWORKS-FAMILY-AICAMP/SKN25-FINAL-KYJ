from __future__ import annotations

import hashlib

from foldmind_ai_core.core.application.models.projection_inputs import (
    ProjectionDocument,
    ProjectionDocumentFolderRelationSnapshot,
    ProjectionDocumentProfile,
    ProjectionDocumentSignal,
    ProjectionFolder,
    ProjectionFolderSignal,
)
from foldmind_ai_core.core.application.projections.graph import (
    DocumentFolderRelationProjection,
    DocumentSignalNodeProjection,
    DocumentRelationshipProjection,
    DocumentSignalProjection,
    FolderRelationshipProjection,
    FolderSignalNodeProjection,
    FolderSignalProjection,
)
from foldmind_ai_core.core.application.projections.vector import (
    DocumentSignalVectorProjection,
    DocumentVectorProjection,
    FolderSignalVectorProjection,
    FolderVectorProjection,
)


def document_vector_projection_from_profile(
    profile: ProjectionDocumentProfile,
    signals: tuple[ProjectionDocumentSignal, ...],
    *,
    embedding_model: str,
    embedding_version: str,
    index_schema_version: str,
) -> DocumentVectorProjection:
    embedding_input = _projection_text(
        (
            profile.title,
            *(signal.text for signal in signals if signal.document_id == profile.document_id),
        )
    )
    return DocumentVectorProjection(
        tenant=profile.tenant,
        document_type=profile.document_type,
        document_id=profile.document_id,
        source_version=profile.source_version,
        content_digest=profile.content_digest,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        embedding_input=embedding_input,
        embedding_input_hash=_content_hash(embedding_input),
        embedding_model=embedding_model,
        embedding_version=embedding_version,
        index_schema_version=index_schema_version,
    )


def signal_vector_projection_from_signal(
    signal: ProjectionDocumentSignal,
    *,
    embedding_model: str,
    embedding_version: str,
    index_schema_version: str,
) -> DocumentSignalVectorProjection:
    return DocumentSignalVectorProjection(
        signal_id=signal.signal_id,
        tenant=signal.tenant,
        document_type=signal.document_type,
        document_id=signal.document_id,
        signal_type=signal.signal_type,
        signal_key=signal.signal_key,
        source_version=signal.source_version,
        content_digest=signal.content_digest,
        attributes=dict(signal.attributes),
        confidence=signal.confidence,
        evidence=signal.evidence,
        embedding_input=signal.text,
        embedding_input_hash=_content_hash(signal.text),
        embedding_model=embedding_model,
        embedding_version=embedding_version,
        index_schema_version=index_schema_version,
        metadata=dict(signal.metadata),
    )


def folder_signal_vector_projection_from_signal(
    signal: ProjectionFolderSignal,
    *,
    embedding_model: str,
    embedding_version: str,
    index_schema_version: str,
) -> FolderSignalVectorProjection:
    return FolderSignalVectorProjection(
        signal_id=signal.signal_id,
        tenant=signal.tenant,
        folder_id=signal.folder_id,
        signal_type=signal.signal_type,
        signal_key=signal.signal_key,
        source_version=signal.source_version,
        related_document_id=signal.related_document_id,
        attributes=dict(signal.attributes),
        confidence=signal.confidence,
        evidence=tuple(dict(item) for item in signal.evidence),
        embedding_input=signal.text,
        embedding_input_hash=_content_hash(signal.text),
        embedding_model=embedding_model,
        embedding_version=embedding_version,
        index_schema_version=index_schema_version,
        metadata=dict(signal.metadata),
    )


def folder_vector_projection_from_source(
    folder: ProjectionFolder,
    signals: tuple[ProjectionFolderSignal, ...] = (),
    *,
    embedding_model: str,
    embedding_version: str,
    index_schema_version: str,
) -> FolderVectorProjection:
    embedding_input = _projection_text(
        (
            folder.name,
            folder.path or "",
            folder.description,
            *(
                signal.text
                for signal in signals
                if signal.signal_type in ("summary", "responsibility")
            ),
        )
    )
    return FolderVectorProjection(
        tenant=folder.tenant,
        folder_id=folder.folder_id,
        source_version=folder.source_version,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        embedding_input=embedding_input,
        embedding_input_hash=_content_hash(embedding_input),
        embedding_model=embedding_model,
        embedding_version=embedding_version,
        index_schema_version=index_schema_version,
    )


def document_relationship_projection_from_source_document(
    document: ProjectionDocument,
) -> DocumentRelationshipProjection:
    return DocumentRelationshipProjection(
        tenant=document.tenant,
        document_type=document.document_type,
        document_id=document.document_id,
        source_version=document.source_version,
        content_digest=_source_content_digest(document),
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def document_folder_relation_projection_from_snapshot(
    snapshot: ProjectionDocumentFolderRelationSnapshot,
) -> DocumentFolderRelationProjection:
    return DocumentFolderRelationProjection(
        tenant=snapshot.tenant,
        document_id=snapshot.document_id,
        source_version=snapshot.source_version,
        folder_ids=snapshot.folder_ids,
    )


def signal_graph_projection_from_signal(
    signal: ProjectionDocumentSignal,
) -> DocumentSignalNodeProjection:
    return DocumentSignalNodeProjection(
        signal_id=signal.signal_id,
        tenant=signal.tenant,
        signal_type=signal.signal_type,
        signal_key=signal.signal_key,
        text=signal.text,
        document_id=signal.document_id,
        source_version=signal.source_version,
        content_digest=signal.content_digest,
        attributes=dict(signal.attributes),
        confidence=signal.confidence,
        metadata=dict(signal.metadata),
    )


def document_signal_graph_projection_from_profile(
    profile: ProjectionDocumentProfile,
    signals: tuple[ProjectionDocumentSignal, ...],
) -> DocumentSignalProjection:
    return DocumentSignalProjection(
        tenant=profile.tenant,
        document_type=profile.document_type,
        document_id=profile.document_id,
        source_version=profile.source_version,
        content_digest=profile.content_digest,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        title=profile.title,
        signal_set_version=profile.signal_set_version,
        signals=tuple(signal_graph_projection_from_signal(signal) for signal in signals),
        metadata={
            "model": profile.model,
        },
    )


def folder_signal_graph_projection_from_folder(
    folder: ProjectionFolder,
    signals: tuple[ProjectionFolderSignal, ...],
) -> FolderSignalProjection:
    return FolderSignalProjection(
        tenant=folder.tenant,
        folder_id=folder.folder_id,
        source_version=folder.source_version,
        signals=tuple(
            FolderSignalNodeProjection(
                signal_id=signal.signal_id,
                tenant=signal.tenant,
                folder_id=signal.folder_id,
                source_version=signal.source_version,
                signal_type=signal.signal_type,
                signal_key=signal.signal_key,
                text=signal.text,
                related_document_id=signal.related_document_id,
                attributes=dict(signal.attributes),
                confidence=signal.confidence,
                metadata=dict(signal.metadata),
            )
            for signal in signals
        ),
    )


def folder_relationship_projection_from_source_folder(
    folder: ProjectionFolder,
) -> FolderRelationshipProjection:
    return FolderRelationshipProjection(
        tenant=folder.tenant,
        folder_id=folder.folder_id,
        source_version=folder.source_version,
        name=folder.name,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        path=folder.path,
        parent_folder_id=folder.parent_folder_id,
    )


def _projection_text(parts: tuple[str, ...]) -> str:
    return "\n\n".join(part.strip() for part in parts if part.strip())


def _content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _source_content_digest(document: ProjectionDocument) -> str:
    digest = getattr(document, "content_digest", "")
    if isinstance(digest, str) and digest.strip():
        return digest
    full_text = getattr(document, "full_text", "")
    if isinstance(full_text, str) and full_text:
        return _content_hash(full_text)
    return ""
