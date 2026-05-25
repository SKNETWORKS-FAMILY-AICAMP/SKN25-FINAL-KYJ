from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.domain.models.document_signals import DocumentSignal
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(frozen=True, slots=True)
class DocumentIndexingInvariantService:
    def validate_indexed_context(
        self,
        *,
        document: SourceDocument,
        chunks: tuple[DocumentChunk, ...],
        index_state: DocumentIndexState,
        signals: tuple[DocumentSignal, ...],
    ) -> None:
        expected_context = (
            document.tenant,
            document.document_id,
            document.source_version,
        )
        for value, field_name in (
            (document.tenant, "document.tenant"),
            (document.document_id, "document.document_id"),
            (document.source_version, "document.source_version"),
        ):
            _required_text(value, field_name)
        if not chunks:
            raise InvalidInputError("document indexed context must include chunks.")
        document_index_input_digest = index_state.document_index_input_digest
        document_signal_input_digest = index_state.document_signal_input_digest
        _required_text(document_index_input_digest, "document_index_input_digest")
        _required_text(document_signal_input_digest, "document_signal_input_digest")
        if (
            not isinstance(index_state.signal_generation_version, str)
            or not index_state.signal_generation_version.strip()
        ):
            raise InvalidInputError(
                "document index state signal_generation_version must not be blank."
            )
        if (
            index_state.document_id != document.document_id
            or any(
                (
                    chunk.tenant,
                    chunk.document_id,
                    chunk.source_version,
                )
                != expected_context
                or chunk.document_index_input_digest != document_index_input_digest
                for chunk in chunks
            )
            or any(
                (
                    signal.tenant,
                    signal.document_id,
                    signal.source_version,
                )
                != expected_context
                or signal.document_signal_input_digest != document_signal_input_digest
                or signal.signal_generation_version
                != index_state.signal_generation_version
                for signal in signals
            )
        ):
            raise InvalidInputError(
                "document indexed event context must match the source document."
            )


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError(f"{name} must not be blank.")
    return value.strip()
