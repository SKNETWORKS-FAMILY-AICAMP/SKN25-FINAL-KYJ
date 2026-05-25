from __future__ import annotations

from foldmind_ai_core.adapters.outbound.postgres.models.document_projections import (
    DocumentSignalRow,
)
from foldmind_ai_core.adapters.outbound.postgres.models.folder_projections import (
    FolderSignalRow,
)
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
    DocumentSignalEvidence,
)
from foldmind_ai_core.core.domain.models.folder_signals import FolderSignal
from foldmind_ai_core.shared.types import JsonObject


def document_signal_row_from_domain(
    signal: DocumentSignal,
) -> DocumentSignalRow:
    return DocumentSignalRow(
        signal_id=signal.signal_id,
        document_id=signal.document_id,
        document_signal_input_digest=signal.document_signal_input_digest,
        signal_generation_version=signal.signal_generation_version,
        signal_type=str(signal.signal_type),
        signal_key=signal.signal_key,
        text=signal.text,
        attributes_json=dict(signal.attributes),
        evidence_json=[signal_evidence_json(evidence) for evidence in signal.evidence],
        confidence=signal.confidence,
        extractor_name=signal.extractor_name,
        extractor_version=signal.extractor_version,
        generation_model=signal.generation_model,
    )


def folder_signal_row_from_domain(
    signal: FolderSignal,
) -> FolderSignalRow:
    return FolderSignalRow(
        signal_id=signal.signal_id,
        folder_id=signal.folder_id,
        folder_signal_input_digest=signal.folder_signal_input_digest,
        signal_generation_version=signal.signal_generation_version,
        signal_type=str(signal.signal_type),
        signal_key=signal.signal_key,
        text=signal.text,
        related_document_id=signal.related_document_id,
        attributes_json=dict(signal.attributes),
        evidence_json=[dict(item) for item in signal.evidence],
        confidence=signal.confidence,
        extractor_name=signal.extractor_name,
        extractor_version=signal.extractor_version,
        generation_model=signal.generation_model,
    )


def signal_evidence_json(evidence: DocumentSignalEvidence) -> JsonObject:
    return {
        "chunk_id": evidence.chunk_id,
        "quote": evidence.quote,
        "start_offset": evidence.start_offset,
        "end_offset": evidence.end_offset,
        "metadata": dict(evidence.metadata),
    }


def document_signal_texts_from_rows(rows: list[DocumentSignalRow]) -> tuple[str, ...]:
    texts: list[str] = []
    for row in sorted(rows, key=_signal_sort_key):
        text = row.text.strip()
        if text:
            texts.append(text)
    return tuple(texts)


def _signal_sort_key(row: DocumentSignalRow) -> tuple[int, float, str, str]:
    confidence = row.confidence
    confidence_score = confidence if isinstance(confidence, int | float) else -1.0
    return (
        _signal_type_order(row.signal_type),
        -float(confidence_score),
        row.signal_key,
        row.signal_id,
    )


def _signal_type_order(signal_type: str) -> int:
    return {
        "summary": 0,
        "concept": 1,
        "entity": 2,
        "issue": 3,
        "commitment": 4,
        "claim": 5,
    }.get(signal_type, 6)
