from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import JsonObject


@dataclass(frozen=True, slots=True)
class PostgresDocumentSignalRecord:
    signal_id: str
    signal_type: str
    signal_key: str
    text: str
    attributes: JsonObject = field(default_factory=dict)
    evidence: tuple[JsonObject, ...] = ()
    confidence: float | None = None
    extractor_name: str = ""
    extractor_version: str = ""


@dataclass(frozen=True, slots=True)
class PostgresFolderSignalRecord:
    signal_id: str
    folder_id: str
    folder_signal_input_revision: int
    signal_type: str
    signal_key: str
    text: str
    related_document_id: str | None = None
    attributes: JsonObject = field(default_factory=dict)
    evidence: tuple[JsonObject, ...] = ()
    confidence: float | None = None
    extractor_name: str = ""
    extractor_version: str = ""
