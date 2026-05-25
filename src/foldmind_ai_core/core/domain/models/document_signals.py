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


@dataclass(frozen=True, slots=True)
class DocumentSignalEvidence:
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
    signal_type: DocumentSignalType
    signal_key: str
    text: str
    extractor_name: str
    extractor_version: str
    signal_generation_version: str = "1"
    attributes: JsonObject = field(default_factory=dict)
    evidence: tuple[DocumentSignalEvidence, ...] = ()
    confidence: float | None = None
    generation_model: str | None = None
    metadata: Metadata = field(default_factory=dict)
