from __future__ import annotations

from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.profiling import DocumentProfile, DocumentSignal
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.shared.validation import InvalidInputError


def validate_document_indexed_context(
    *,
    document: SourceDocument,
    chunks: tuple[DocumentChunk, ...],
    profile: DocumentProfile,
    signals: tuple[DocumentSignal, ...],
) -> None:
    expected_context = (
        document.tenant,
        document.document_id,
        document.source_version,
    )
    profile_context = (
        profile.tenant,
        profile.document_id,
        profile.source_version,
    )
    document_index_input_digest = profile.document_index_input_digest
    document_signal_input_digest = profile.document_signal_input_digest
    if not profile.signal_generation_version.strip():
        raise InvalidInputError(
            "document profile signal_generation_version must not be blank."
        )
    if (
        profile_context != expected_context
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
            or signal.signal_generation_version != profile.signal_generation_version
            for signal in signals
        )
    ):
        raise InvalidInputError(
            "document indexed event projection context must match the source document."
        )
