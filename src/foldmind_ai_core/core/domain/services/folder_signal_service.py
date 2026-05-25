from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from foldmind_ai_core.core.domain.models.confidence import Confidence
from foldmind_ai_core.core.domain.models.folder_signals import (
    FolderSignal,
    FolderSignalType,
)
from foldmind_ai_core.core.domain.services.confidence_service import ConfidenceService
from foldmind_ai_core.shared.types import JsonObject, Metadata
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(frozen=True, slots=True)
class FolderSignalService:
    confidence: ConfidenceService = field(default_factory=ConfidenceService)

    def signal_type(self, value: FolderSignalType | str) -> FolderSignalType:
        try:
            return FolderSignalType(value)
        except (TypeError, ValueError) as exc:
            raise InvalidInputError("unsupported folder signal type.") from exc

    def signal_id(
        self,
        *,
        tenant: str,
        folder_id: str,
        folder_signal_input_digest: str,
        signal_type: FolderSignalType | str,
        signal_key: str,
        related_document_id: str | None = None,
        signal_generation_version: str = "1",
    ) -> str:
        parts = (
            _required_text(tenant, "tenant"),
            _required_text(folder_id, "folder_id"),
            _required_text(folder_signal_input_digest, "folder_signal_input_digest"),
            _required_text(signal_generation_version, "signal_generation_version"),
            self.signal_type(signal_type).value,
            _required_text(signal_key, "signal_key"),
            _optional_identity_text(related_document_id, "related_document_id"),
        )
        digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
        return f"folder-signal-{digest}"

    def create(
        self,
        *,
        tenant: str,
        folder_id: str,
        source_version: str,
        folder_signal_input_digest: str,
        signal_type: FolderSignalType | str,
        signal_key: str,
        text: str,
        related_document_id: str | None = None,
        attributes: JsonObject | None = None,
        evidence: Iterable[JsonObject] = (),
        confidence: Confidence | float | None = None,
        extractor_name: str,
        extractor_version: str,
        generation_model: str | None = None,
        metadata: Metadata | None = None,
        signal_generation_version: str = "1",
    ) -> FolderSignal:
        resolved_type = self.signal_type(signal_type)
        clean_tenant = _required_text(tenant, "tenant")
        clean_folder_id = _required_text(folder_id, "folder_id")
        clean_source_version = _required_text(source_version, "source_version")
        clean_folder_signal_input_digest = _required_text(
            folder_signal_input_digest,
            "folder_signal_input_digest",
        )
        clean_signal_generation_version = _required_text(
            signal_generation_version,
            "signal_generation_version",
        )
        clean_extractor_name = _required_text(extractor_name, "extractor_name")
        clean_extractor_version = _required_text(extractor_version, "extractor_version")
        clean_key = _required_text(signal_key, "signal_key")
        clean_related_document_id = (
            _required_text(related_document_id, "related_document_id")
            if related_document_id is not None
            else None
        )
        clean_text = _required_text(text, "text")
        return FolderSignal(
            signal_id=self.signal_id(
                tenant=clean_tenant,
                folder_id=clean_folder_id,
                folder_signal_input_digest=clean_folder_signal_input_digest,
                signal_generation_version=clean_signal_generation_version,
                signal_type=resolved_type,
                signal_key=clean_key,
                related_document_id=clean_related_document_id,
            ),
            tenant=clean_tenant,
            folder_id=clean_folder_id,
            source_version=clean_source_version,
            folder_signal_input_digest=clean_folder_signal_input_digest,
            signal_generation_version=clean_signal_generation_version,
            signal_type=resolved_type,
            signal_key=clean_key,
            text=clean_text,
            related_document_id=clean_related_document_id,
            attributes=_json_object(attributes, "attributes"),
            evidence=tuple(_json_object(item, "evidence item") for item in evidence),
            confidence=self.confidence.normalize(confidence),
            extractor_name=clean_extractor_name,
            extractor_version=clean_extractor_version,
            generation_model=_optional_text(generation_model, "generation_model"),
            metadata=_json_object(metadata, "metadata"),
        )


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError(f"{name} must not be blank.")
    return value.strip()


def _optional_identity_text(value: object, name: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise InvalidInputError(f"{name} must be a string.")
    stripped = value.strip()
    if not stripped:
        raise InvalidInputError(f"{name} must not be blank.")
    return stripped


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
