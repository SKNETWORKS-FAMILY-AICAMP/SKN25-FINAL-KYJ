from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from foldmind_ai_core.core.domain.models.confidence import Confidence
from foldmind_ai_core.core.domain.models.profiling import (
    DocumentSignal,
    DocumentSignalType,
    FolderSignal,
    FolderSignalType,
    SignalEvidence,
)
from foldmind_ai_core.core.domain.services.confidence import normalize_confidence_value
from foldmind_ai_core.shared.types import JsonObject, Metadata
from foldmind_ai_core.shared.validation import InvalidInputError

_SEPARATOR_PATTERN = re.compile(r"[^\w]+", re.UNICODE)
_HASH_PREFIX_LENGTH = 16


@dataclass(frozen=True, slots=True)
class SignalDefinitionRegistry:
    signal_types: tuple[DocumentSignalType, ...]

    def require(self, signal_type: DocumentSignalType | str) -> DocumentSignalType:
        resolved = document_signal_type(signal_type)
        if resolved not in self.signal_types:
            raise InvalidInputError(f"unsupported document signal type: {resolved}.")
        return resolved

    def allowed_types(self) -> tuple[DocumentSignalType, ...]:
        return self.signal_types


DEFAULT_SIGNAL_DEFINITIONS = SignalDefinitionRegistry(
    signal_types=(
        DocumentSignalType.SUMMARY,
        DocumentSignalType.CONCEPT,
        DocumentSignalType.ENTITY,
        DocumentSignalType.ISSUE,
        DocumentSignalType.COMMITMENT,
        DocumentSignalType.CLAIM,
    )
)


def document_signal_type(value: DocumentSignalType | str) -> DocumentSignalType:
    try:
        return DocumentSignalType(value)
    except ValueError as exc:
        raise InvalidInputError("unsupported document signal type.") from exc


def folder_signal_type(value: FolderSignalType | str) -> FolderSignalType:
    try:
        return FolderSignalType(value)
    except ValueError as exc:
        raise InvalidInputError("unsupported folder signal type.") from exc


def normalized_signal_label(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidInputError("signal label must be a string.")
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = _SEPARATOR_PATTERN.sub("_", normalized)
    return normalized.strip("_")


def signal_key_for_type(
    *,
    signal_type: DocumentSignalType | str,
    text: str,
    attributes: Mapping[str, object] | None = None,
) -> str:
    resolved = DEFAULT_SIGNAL_DEFINITIONS.require(signal_type)
    if resolved == DocumentSignalType.SUMMARY:
        return "document-summary"
    if resolved in (DocumentSignalType.CONCEPT, DocumentSignalType.ENTITY):
        candidate = _payload_text(attributes or {}, "key") or _payload_text(
            attributes or {},
            "label",
        )
        key = normalized_signal_label(candidate or text)
        if not key:
            raise InvalidInputError("concept/entity signal key must not be blank.")
        return key
    normalized_text = unicodedata.normalize("NFKC", text).casefold().strip()
    if not normalized_text:
        raise InvalidInputError("signal text must not be blank.")
    digest = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    return digest[:_HASH_PREFIX_LENGTH]


def document_signal_id(
    *,
    tenant: str,
    document_id: str,
    source_version: str,
    signal_type: DocumentSignalType | str,
    signal_key: str,
) -> str:
    parts = (
        _required_text(tenant, "tenant"),
        _required_text(document_id, "document_id"),
        _required_text(source_version, "source_version"),
        DEFAULT_SIGNAL_DEFINITIONS.require(signal_type).value,
        _required_text(signal_key, "signal_key"),
    )
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"signal-{digest}"


def create_document_signal(
    *,
    tenant: str,
    document_type: str | None,
    document_id: str,
    source_version: str,
    signal_type: DocumentSignalType | str,
    text: str,
    attributes: JsonObject | None,
    evidence: Iterable[SignalEvidence],
    confidence: Confidence | float | None,
    extractor_name: str,
    extractor_version: str,
    metadata: Metadata | None = None,
) -> DocumentSignal:
    resolved_type = DEFAULT_SIGNAL_DEFINITIONS.require(signal_type)
    clean_text = _required_text(text, "text")
    signal_attributes = dict(attributes or {})
    evidence_tuple = tuple(_validated_signal_evidence(item) for item in evidence)
    if not evidence_tuple:
        raise InvalidInputError("document signal evidence must not be empty.")
    _required_text(document_id, "document_id")
    _required_text(extractor_name, "extractor_name")
    _required_text(extractor_version, "extractor_version")
    signal_key = signal_key_for_type(
        signal_type=resolved_type,
        text=clean_text,
        attributes=signal_attributes,
    )
    return DocumentSignal(
        signal_id=document_signal_id(
            tenant=tenant,
            document_id=document_id,
            source_version=source_version,
            signal_type=resolved_type,
            signal_key=signal_key,
        ),
        tenant=tenant,
        document_type=document_type,
        document_id=document_id,
        source_version=source_version,
        signal_type=resolved_type,
        signal_key=signal_key,
        text=clean_text,
        attributes=signal_attributes,
        evidence=evidence_tuple,
        confidence=normalize_confidence_value(confidence),
        extractor_name=extractor_name,
        extractor_version=extractor_version,
        metadata=dict(metadata or {}),
    )


def folder_signal_id(
    *,
    tenant: str,
    folder_id: str,
    source_version: str,
    signal_type: FolderSignalType | str,
    signal_key: str,
    related_document_id: str | None = None,
) -> str:
    parts = (
        _required_text(tenant, "tenant"),
        _required_text(folder_id, "folder_id"),
        _required_text(source_version, "source_version"),
        folder_signal_type(signal_type).value,
        _required_text(signal_key, "signal_key"),
        related_document_id.strip() if related_document_id else "",
    )
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"folder-signal-{digest}"


def create_folder_signal(
    *,
    tenant: str,
    folder_id: str,
    source_version: str,
    signal_type: FolderSignalType | str,
    signal_key: str,
    text: str,
    related_document_id: str | None = None,
    attributes: JsonObject | None = None,
    evidence: Iterable[JsonObject] = (),
    confidence: Confidence | float | None = None,
    extractor_name: str,
    extractor_version: str,
    metadata: Metadata | None = None,
) -> FolderSignal:
    resolved_type = folder_signal_type(signal_type)
    clean_key = _required_text(signal_key, "signal_key")
    clean_related_document_id = (
        _required_text(related_document_id, "related_document_id")
        if related_document_id is not None
        else None
    )
    clean_text = _required_text(text, "text")
    _required_text(extractor_name, "extractor_name")
    _required_text(extractor_version, "extractor_version")
    return FolderSignal(
        signal_id=folder_signal_id(
            tenant=tenant,
            folder_id=folder_id,
            source_version=source_version,
            signal_type=resolved_type,
            signal_key=clean_key,
            related_document_id=clean_related_document_id,
        ),
        tenant=_required_text(tenant, "tenant"),
        folder_id=_required_text(folder_id, "folder_id"),
        source_version=_required_text(source_version, "source_version"),
        signal_type=resolved_type,
        signal_key=clean_key,
        text=clean_text,
        related_document_id=clean_related_document_id,
        attributes=dict(attributes or {}),
        evidence=tuple(dict(item) for item in evidence),
        confidence=normalize_confidence_value(confidence),
        extractor_name=extractor_name.strip(),
        extractor_version=extractor_version.strip(),
        metadata=dict(metadata or {}),
    )


def _validated_signal_evidence(evidence: SignalEvidence) -> SignalEvidence:
    if not isinstance(evidence, SignalEvidence):
        raise InvalidInputError("document signal evidence must be SignalEvidence.")
    validated = SignalEvidence(
        chunk_id=_required_text(evidence.chunk_id, "chunk_id"),
        quote=_required_text(evidence.quote, "quote"),
        start_offset=_optional_int(evidence.start_offset, "start_offset"),
        end_offset=_optional_int(evidence.end_offset, "end_offset"),
        metadata=dict(evidence.metadata),
    )
    if (
        validated.start_offset is not None
        and validated.end_offset is not None
        and validated.end_offset < validated.start_offset
    ):
        raise InvalidInputError("end_offset must be greater than or equal to start_offset.")
    return validated


def _payload_text(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidInputError(f"{key} must be a string.")
    return value.strip() or None


def _optional_int(value: object, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidInputError(f"{name} must be a non-negative integer.")
    return value


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError(f"{name} must not be blank.")
    return value.strip()
