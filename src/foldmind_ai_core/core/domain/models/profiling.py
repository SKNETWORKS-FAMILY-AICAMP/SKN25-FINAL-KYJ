from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from foldmind_ai_core.shared.types import JsonObject, Metadata


class DocumentSignalType(StrEnum):
    SUMMARY = "summary"
    CONCEPT = "concept"
    ENTITY = "entity"
    ISSUE = "issue"
    COMMITMENT = "commitment"
    CLAIM = "claim"


class FolderSignalType(StrEnum):
    SUMMARY = "summary"
    RESPONSIBILITY = "responsibility"
    ALIGNMENT = "alignment"
    COHERENCE = "coherence"
    OUTLIER_DOCUMENT = "outlier_document"
    COVERAGE_GAP = "coverage_gap"
    NAMING_MISMATCH = "naming_mismatch"
    SPLIT_SUGGESTION = "split_suggestion"
    MERGE_SUGGESTION = "merge_suggestion"


@dataclass(frozen=True, slots=True)
class SignalEvidence:
    chunk_id: str
    quote: str
    start_offset: int | None = None
    end_offset: int | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentSignal:
    signal_id: str
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    document_signal_input_digest: str
    signal_type: DocumentSignalType | str
    signal_key: str
    text: str
    signal_generation_version: str = "1"
    attributes: JsonObject = field(default_factory=dict)
    evidence: tuple[SignalEvidence, ...] = ()
    confidence: float | None = None
    extractor_name: str = ""
    extractor_version: str = ""
    generation_model: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FolderSignal:
    signal_id: str
    tenant: str
    folder_id: str
    source_version: str
    folder_signal_input_digest: str
    signal_type: FolderSignalType | str
    signal_key: str
    text: str
    signal_generation_version: str = "1"
    related_document_id: str | None = None
    attributes: JsonObject = field(default_factory=dict)
    evidence: tuple[JsonObject, ...] = ()
    confidence: float | None = None
    extractor_name: str = ""
    extractor_version: str = ""
    generation_model: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentProfile:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    created_at: str
    updated_at: str
    title: str
    document_index_input_digest: str
    document_signal_input_digest: str
    signal_generation_version: str = "1"
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentSignalExtraction:
    profile: DocumentProfile
    signals: tuple[DocumentSignal, ...]


@dataclass(frozen=True, slots=True)
class FolderSignalExtraction:
    signals: tuple[FolderSignal, ...]
    signal_generation_version: str = "1"
