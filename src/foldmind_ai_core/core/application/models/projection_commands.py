from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.models.vector_projection import (
    DocumentChunkVectorProjection,
)
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_signals import DocumentSignal
from foldmind_ai_core.core.domain.models.document_sources import DocumentSourceState
from foldmind_ai_core.core.domain.models.folder_signals import FolderSignal
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder


@dataclass(frozen=True, slots=True)
class ProjectDocumentCommand:
    document: DocumentSourceState
    chunks: tuple[DocumentChunkVectorProjection, ...]
    document_index: DocumentIndexState
    signals: tuple[DocumentSignal, ...]


@dataclass(frozen=True, slots=True)
class ProjectDocumentFolderRelationsCommand:
    folder_relation_snapshot: SourceDocumentFolderRelationSnapshot


@dataclass(frozen=True, slots=True)
class DeleteDocumentProjectionCommand:
    tenant: str
    document_id: str
    affected_folder_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectFolderCommand:
    folder: SourceFolder


@dataclass(frozen=True, slots=True)
class ProjectFolderSignalsCommand:
    folder: SourceFolder
    folder_signal_input_digest: str
    signal_generation_version: str = "1"
    signals: tuple[FolderSignal, ...] = ()


@dataclass(frozen=True, slots=True)
class InvalidateFolderSignalsCommand:
    tenant: str
    folder_id: str
    folder_signal_input_digest: str


@dataclass(frozen=True, slots=True)
class DeleteFolderProjectionCommand:
    tenant: str
    folder_id: str
