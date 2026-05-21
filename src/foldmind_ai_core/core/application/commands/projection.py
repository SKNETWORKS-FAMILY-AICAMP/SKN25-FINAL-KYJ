from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.models.projection_inputs import (
    ProjectionDocument,
    ProjectionDocumentFolderRelationSnapshot,
    ProjectionDocumentProfile,
    ProjectionFolder,
    ProjectionDocumentSignal,
    ProjectionFolderSignal,
)
from foldmind_ai_core.core.application.projections.vector import DocumentChunkVectorProjection


@dataclass(frozen=True, slots=True)
class ProjectDocumentCommand:
    document: ProjectionDocument
    chunks: tuple[DocumentChunkVectorProjection, ...]
    profile: ProjectionDocumentProfile
    signals: tuple[ProjectionDocumentSignal, ...]


@dataclass(frozen=True, slots=True)
class ProjectDocumentFolderRelationsCommand:
    folder_relation_snapshot: ProjectionDocumentFolderRelationSnapshot


@dataclass(frozen=True, slots=True)
class DeleteDocumentProjectionCommand:
    document_id: str
    affected_folder_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectFolderCommand:
    folder: ProjectionFolder


@dataclass(frozen=True, slots=True)
class ProjectFolderSignalsCommand:
    folder: ProjectionFolder
    folder_signal_input_digest: str
    signal_generation_version: str = "1"
    signals: tuple[ProjectionFolderSignal, ...] = ()


@dataclass(frozen=True, slots=True)
class InvalidateFolderSignalsCommand:
    tenant: str
    folder_id: str
    folder_signal_input_digest: str


@dataclass(frozen=True, slots=True)
class DeleteFolderProjectionCommand:
    folder_id: str
