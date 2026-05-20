from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.models.projection_inputs import (
    ProjectionDocument,
    ProjectionDocumentFolderRelationSnapshot,
    ProjectionDocumentProfile,
    ProjectionDocumentSignal,
    ProjectionFolder,
    ProjectionFolderSignal,
)
from foldmind_ai_core.core.application.projections.vector import DocumentChunkVectorProjection


@dataclass(frozen=True, slots=True)
class DocumentIndexedProjectionEvent:
    document: ProjectionDocument
    chunks: tuple[DocumentChunkVectorProjection, ...]
    profile: ProjectionDocumentProfile
    signals: tuple[ProjectionDocumentSignal, ...]


@dataclass(frozen=True, slots=True)
class DocumentFolderRelationsIndexedProjectionEvent:
    folder_relation_snapshot: ProjectionDocumentFolderRelationSnapshot


@dataclass(frozen=True, slots=True)
class DocumentDeletedProjectionEvent:
    document_id: str
    affected_folder_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FolderIndexedProjectionEvent:
    folder: ProjectionFolder


@dataclass(frozen=True, slots=True)
class FolderSignalsIndexedProjectionEvent:
    folder: ProjectionFolder
    index_input_digest: str
    signal_generation_version: str = "1"
    signals: tuple[ProjectionFolderSignal, ...] = ()


@dataclass(frozen=True, slots=True)
class FolderSignalsInvalidatedProjectionEvent:
    tenant: str
    folder_id: str
    index_input_digest: str
    signal_generation_version: str = "1"


@dataclass(frozen=True, slots=True)
class FolderDeletedProjectionEvent:
    folder_id: str
