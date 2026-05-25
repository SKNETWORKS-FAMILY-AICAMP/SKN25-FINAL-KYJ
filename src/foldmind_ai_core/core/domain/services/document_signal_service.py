from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from foldmind_ai_core.core.domain.models.confidence import Confidence
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
    DocumentSignalEvidence,
    DocumentSignalType,
)
from foldmind_ai_core.core.domain.services.confidence_service import ConfidenceService
from foldmind_ai_core.shared.input_digest import input_digest
from foldmind_ai_core.shared.types import JsonObject, Metadata
from foldmind_ai_core.shared.validation import InvalidInputError

_SEPARATOR_PATTERN = re.compile(r"[^\w]+", re.UNICODE)
_HASH_PREFIX_LENGTH = 16
DEFAULT_DOCUMENT_SIGNAL_TYPES = (
    DocumentSignalType.SUMMARY,
    DocumentSignalType.CONCEPT,
    DocumentSignalType.ENTITY,
    DocumentSignalType.ISSUE,
    DocumentSignalType.COMMITMENT,
    DocumentSignalType.CLAIM,
)


@dataclass(frozen=True, slots=True)
class DocumentSignalService:
    allowed_signal_types: tuple[DocumentSignalType, ...] = DEFAULT_DOCUMENT_SIGNAL_TYPES
    confidence: ConfidenceService = field(default_factory=ConfidenceService)

    def signal_type(self, value: DocumentSignalType | str) -> DocumentSignalType:
        try:
            signal_type = DocumentSignalType(value)
        except (TypeError, ValueError) as exc:
            raise InvalidInputError("unsupported document signal type.") from exc
        if signal_type not in self.allowed_signal_types:
            raise InvalidInputError(f"unsupported document signal type: {signal_type}.")
        return signal_type

    def normalized_label(self, value: str) -> str:
        if not isinstance(value, str):
            raise InvalidInputError("signal label must be a string.")
        normalized = unicodedata.normalize("NFKC", value).casefold().strip()
        normalized = _SEPARATOR_PATTERN.sub("_", normalized)
        return normalized.strip("_")

    def key_for_type(
        self,
        *,
        signal_type: DocumentSignalType | str,
        text: str,
        attributes: Mapping[str, object] | None = None,
    ) -> str:
        resolved = self.signal_type(signal_type)
        if resolved == DocumentSignalType.SUMMARY:
            return "document-summary"
        if resolved in (DocumentSignalType.CONCEPT, DocumentSignalType.ENTITY):
            candidate = _payload_text(attributes or {}, "key") or _payload_text(
                attributes or {},
                "label",
            )
            key = self.normalized_label(candidate or text)
            if not key:
                raise InvalidInputError("concept/entity signal key must not be blank.")
            return key
        normalized_text = unicodedata.normalize("NFKC", text).casefold().strip()
        if not normalized_text:
            raise InvalidInputError("signal text must not be blank.")
        digest = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        return digest[:_HASH_PREFIX_LENGTH]

    def signal_id(
        self,
        *,
        tenant: str,
        document_id: str,
        document_signal_input_digest: str,
        signal_type: DocumentSignalType | str,
        signal_key: str,
        signal_generation_version: str = "1",
    ) -> str:
        parts = (
            _required_text(tenant, "tenant"),
            _required_text(document_id, "document_id"),
            _required_text(
                document_signal_input_digest,
                "document_signal_input_digest",
            ),
            _required_text(signal_generation_version, "signal_generation_version"),
            self.signal_type(signal_type).value,
            _required_text(signal_key, "signal_key"),
        )
        digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
        return f"signal-{digest}"

    def input_digest(
        self,
        *,
        document_index_input_digest: str,
        signal_generation_version: str,
    ) -> str:
        return input_digest(
            "document_signal",
            {
                "document_index_input_digest": _required_text(
                    document_index_input_digest,
                    "document_index_input_digest",
                ),
                "signal_generation_version": _required_text(
                    signal_generation_version,
                    "signal_generation_version",
                ),
            },
        )

    def create(
        self,
        *,
        tenant: str,
        document_type: str | None,
        document_id: str,
        source_version: str,
        document_signal_input_digest: str,
        signal_type: DocumentSignalType | str,
        text: str,
        attributes: JsonObject | None,
        evidence: Iterable[DocumentSignalEvidence],
        confidence: Confidence | float | None,
        extractor_name: str,
        extractor_version: str,
        signal_generation_version: str = "1",
        generation_model: str | None = None,
        metadata: Metadata | None = None,
    ) -> DocumentSignal:
        resolved_type = self.signal_type(signal_type)
        clean_tenant = _required_text(tenant, "tenant")
        clean_document_id = _required_text(document_id, "document_id")
        clean_source_version = _required_text(source_version, "source_version")
        clean_document_signal_input_digest = _required_text(
            document_signal_input_digest,
            "document_signal_input_digest",
        )
        clean_signal_generation_version = _required_text(
            signal_generation_version,
            "signal_generation_version",
        )
        clean_extractor_name = _required_text(extractor_name, "extractor_name")
        clean_extractor_version = _required_text(extractor_version, "extractor_version")
        clean_text = _required_text(text, "text")
        signal_attributes = _json_object(attributes, "attributes")
        evidence_tuple = tuple(_validated_signal_evidence(item) for item in evidence)
        if not evidence_tuple:
            raise InvalidInputError("document signal evidence must not be empty.")
        signal_key = self.key_for_type(
            signal_type=resolved_type,
            text=clean_text,
            attributes=signal_attributes,
        )
        return DocumentSignal(
            signal_id=self.signal_id(
                tenant=clean_tenant,
                document_id=clean_document_id,
                document_signal_input_digest=clean_document_signal_input_digest,
                signal_generation_version=clean_signal_generation_version,
                signal_type=resolved_type,
                signal_key=signal_key,
            ),
            tenant=clean_tenant,
            document_type=document_type,
            document_id=clean_document_id,
            source_version=clean_source_version,
            document_signal_input_digest=clean_document_signal_input_digest,
            signal_generation_version=clean_signal_generation_version,
            signal_type=resolved_type,
            signal_key=signal_key,
            text=clean_text,
            attributes=signal_attributes,
            evidence=evidence_tuple,
            confidence=self.confidence.normalize(confidence),
            extractor_name=clean_extractor_name,
            extractor_version=clean_extractor_version,
            generation_model=_optional_text(generation_model, "generation_model"),
            metadata=_json_object(metadata, "metadata"),
        )


def _validated_signal_evidence(evidence: DocumentSignalEvidence) -> DocumentSignalEvidence:
    if not isinstance(evidence, DocumentSignalEvidence):
        raise InvalidInputError("document signal evidence must be DocumentSignalEvidence.")
    validated = DocumentSignalEvidence(
        chunk_id=_required_text(evidence.chunk_id, "chunk_id"),
        quote=_required_text(evidence.quote, "quote"),
        start_offset=_optional_int(evidence.start_offset, "start_offset"),
        end_offset=_optional_int(evidence.end_offset, "end_offset"),
        metadata=_json_object(evidence.metadata, "evidence.metadata"),
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


def _optional_text(value: object, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidInputError(f"{name} must be a string.")
    stripped = value.strip()
    if not stripped:
        raise InvalidInputError(f"{name} must not be blank.")
    return stripped


def _json_object(value: object, name: str) -> JsonObject:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise InvalidInputError(f"{name} must be a JSON object.")
    result = dict(value)
    if not all(isinstance(key, str) and _is_json_value(item) for key, item in result.items()):
        raise InvalidInputError(f"{name} must contain only JSON-compatible values.")
    return result


def _is_json_value(value: object) -> bool:
    if value is None or isinstance(value, str | int | bool):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_value(item)
            for key, item in value.items()
        )
    return False
