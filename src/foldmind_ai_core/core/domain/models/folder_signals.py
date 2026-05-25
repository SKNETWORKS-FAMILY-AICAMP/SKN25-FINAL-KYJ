from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from foldmind_ai_core.shared.types import JsonObject, Metadata


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
class FolderSignal:
    signal_id: str
    tenant: str
    folder_id: str
    source_version: str
    folder_signal_input_digest: str
    signal_type: FolderSignalType
    signal_key: str
    text: str
    extractor_name: str
    extractor_version: str
    signal_generation_version: str = "1"
    related_document_id: str | None = None
    attributes: JsonObject = field(default_factory=dict)
    evidence: tuple[JsonObject, ...] = ()
    confidence: float | None = None
    generation_model: str | None = None
    metadata: Metadata = field(default_factory=dict)
