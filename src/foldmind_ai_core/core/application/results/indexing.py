from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IndexDocumentResult:
    indexed_chunk_count: int


@dataclass(frozen=True, slots=True)
class IndexFolderResult:
    tenant: str
    folder_id: str
    source_version: str


@dataclass(frozen=True, slots=True)
class EvaluateFolderResponsibilityResult:
    tenant: str
    folder_id: str
    source_version: str
    signal_count: int
