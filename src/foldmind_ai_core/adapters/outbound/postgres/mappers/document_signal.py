from __future__ import annotations

from foldmind_ai_core.adapters.outbound.postgres.models.document_signal import (
    PostgresDocumentSignalRecord,
    PostgresFolderSignalRecord,
)
from foldmind_ai_core.core.domain.models.profiling import (
    DocumentSignal,
    FolderSignal,
    SignalEvidence,
)
from foldmind_ai_core.shared.types import JsonObject


def document_signal_record_from_domain(
    signal: DocumentSignal,
) -> PostgresDocumentSignalRecord:
    return PostgresDocumentSignalRecord(
        signal_id=signal.signal_id,
        signal_type=str(signal.signal_type),
        signal_key=signal.signal_key,
        text=signal.text,
        attributes=dict(signal.attributes),
        evidence=tuple(signal_evidence_json(evidence) for evidence in signal.evidence),
        confidence=signal.confidence,
        extractor_name=signal.extractor_name,
        extractor_version=signal.extractor_version,
    )


def folder_signal_record_from_domain(
    signal: FolderSignal,
) -> PostgresFolderSignalRecord:
    return PostgresFolderSignalRecord(
        signal_id=signal.signal_id,
        folder_id=signal.folder_id,
        signal_type=str(signal.signal_type),
        signal_key=signal.signal_key,
        text=signal.text,
        related_document_id=signal.related_document_id,
        attributes=dict(signal.attributes),
        evidence=tuple(dict(item) for item in signal.evidence),
        confidence=signal.confidence,
        extractor_name=signal.extractor_name,
        extractor_version=signal.extractor_version,
    )


def signal_evidence_json(evidence: SignalEvidence) -> JsonObject:
    return {
        "chunk_id": evidence.chunk_id,
        "quote": evidence.quote,
        "start_offset": evidence.start_offset,
        "end_offset": evidence.end_offset,
        "metadata": dict(evidence.metadata),
    }
