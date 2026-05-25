from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_signals import DocumentSignal
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument


@dataclass(frozen=True, slots=True)
class IndexDocumentCommand:
    document: SourceDocument
    folder_ids: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class DeleteDocumentIndexCommand:
    document_id: str


@dataclass(frozen=True, slots=True)
class DeleteFolderIndexCommand:
    folder_id: str


@dataclass(frozen=True, slots=True)
class IndexDocumentResult:
    indexed_chunk_count: int


@dataclass(frozen=True, slots=True)
class DocumentSignalExtraction:
    index_record: DocumentIndexState
    signals: tuple[DocumentSignal, ...]


@dataclass(frozen=True, slots=True)
class FolderSignalInvalidation:
    tenant: str
    folder_id: str
    folder_signal_input_digest: str
    signal_generation_version: str = "1"
