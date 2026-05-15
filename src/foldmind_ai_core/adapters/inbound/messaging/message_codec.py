from __future__ import annotations

import json
from typing import Any, cast

from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.indexing.outbox import OutboxEvent, OutboxEventType
from foldmind_ai_core.domain.indexing.projection_events import (
    DocumentDeletedProjectionEvent,
    DocumentIndexedProjectionEvent,
    FolderDeletedProjectionEvent,
    FolderIndexedProjectionEvent,
)
from foldmind_ai_core.domain.profiling.models import DocumentProfile, ProfileConcept
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.reference.folders import SourceFolder
from foldmind_ai_core.shared.types import Metadata

DEFAULT_EVENT_SCHEMA_VERSION = "1"

AGGREGATE_TYPE_FIELD_NAMES = ("aggregate_type", "aggregateType", "aggregatetype")
AGGREGATE_ID_FIELD_NAMES = ("aggregate_id", "aggregateId", "aggregateid")
EVENT_KEY_FIELD_NAMES = ("event_key", "eventKey")
EVENT_TYPE_FIELD_NAMES = ("event_type", "eventType", "type")
EVENT_SCHEMA_VERSION_FIELD_NAMES = ("event_schema_version", "eventSchemaVersion")
SEQUENCE_FIELD_NAMES = ("sequence", "event_sequence", "eventSequence")


def outbox_event_key(event: OutboxEvent) -> str:
    return event.event_key


def outbox_event_from_flattened_payload(value: bytes | str | dict[str, Any]) -> OutboxEvent:
    outbox_record = _json_object(value)
    event = OutboxEvent(
        id=_required_text(outbox_record, "id"),
        aggregate_type=_required_text(outbox_record, *AGGREGATE_TYPE_FIELD_NAMES),
        aggregate_id=_required_text(outbox_record, *AGGREGATE_ID_FIELD_NAMES),
        event_type=_required_text(outbox_record, *EVENT_TYPE_FIELD_NAMES),
        sequence=_optional_int(_field(outbox_record, *SEQUENCE_FIELD_NAMES)),
        event_schema_version=_event_schema_version(outbox_record),
        payload=_required_payload(outbox_record),
    )
    _validate_event_key(outbox_record, event)
    return event


def document_indexed_event_from_outbox(
    event: OutboxEvent,
) -> DocumentIndexedProjectionEvent:
    _require_event_type(event, OutboxEventType.DOCUMENT_INDEXED)
    payload = event.payload
    return DocumentIndexedProjectionEvent(
        document=_source_document_from_payload(
            _nested_metadata(payload, "source_document")
        ),
        chunks=_document_chunks_from_payload(payload.get("chunks")),
        profile=_document_profile_from_payload(_nested_metadata(payload, "profile")),
    )


def document_deleted_event_from_outbox(
    event: OutboxEvent,
) -> DocumentDeletedProjectionEvent:
    _require_event_type(event, OutboxEventType.DOCUMENT_DELETED)
    return DocumentDeletedProjectionEvent(
        document_id=str(event.payload["document_id"]),
    )


def folder_indexed_event_from_outbox(
    event: OutboxEvent,
) -> FolderIndexedProjectionEvent:
    _require_event_type(event, OutboxEventType.FOLDER_INDEXED)
    return FolderIndexedProjectionEvent(
        folder=_source_folder_from_payload(
            _nested_metadata(event.payload, "source_folder")
        )
    )


def folder_deleted_event_from_outbox(
    event: OutboxEvent,
) -> FolderDeletedProjectionEvent:
    _require_event_type(event, OutboxEventType.FOLDER_DELETED)
    return FolderDeletedProjectionEvent(
        folder_id=str(event.payload["folder_id"]),
    )


def _require_event_type(event: OutboxEvent, expected: OutboxEventType) -> None:
    actual = OutboxEventType(event.event_type)
    if actual is not expected:
        raise ValueError(f"Expected {expected}, got {actual}.")


def _validate_event_key(record: dict[str, Any], event: OutboxEvent) -> None:
    event_key = _field(record, *EVENT_KEY_FIELD_NAMES)
    if event_key is None:
        return
    if str(event_key) != event.event_key:
        raise ValueError(
            f"Outbox message event_key {event_key!s} does not match {event.event_key}."
        )


def _json_object(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Outbox message value must be a JSON object.")


def _field(record: dict[str, Any], *names: str) -> object | None:
    for name in names:
        if name in record:
            return cast(object, record[name])
    return None


def _required_field(record: dict[str, Any], *names: str) -> object:
    value = _field(record, *names)
    if value is None:
        joined = ", ".join(names)
        raise ValueError(f"Outbox message is missing required field: {joined}.")
    return value


def _required_text(record: dict[str, Any], *names: str) -> str:
    return str(_required_field(record, *names))


def _event_schema_version(record: dict[str, Any]) -> str:
    version = _field(record, *EVENT_SCHEMA_VERSION_FIELD_NAMES)
    if version is None:
        return DEFAULT_EVENT_SCHEMA_VERSION
    return str(version)


def _required_payload(record: dict[str, Any]) -> Metadata:
    payload = _required_field(record, "payload")
    return cast(Metadata, _json_object(payload))


def _source_document_from_payload(payload: Metadata) -> SourceDocument:
    return SourceDocument(
        tenant=str(payload["tenant"]),
        document_type=str(payload["document_type"]),
        document_id=str(payload["document_id"]),
        source_version=str(payload["source_version"]),
        title=str(payload.get("title") or ""),
        body="",
        folder_ids=_string_tuple(payload.get("folder_ids")),
        tag_ids=_string_tuple(payload.get("tag_ids")),
        metadata=_metadata_or_empty(payload.get("metadata")),
    )


def _source_folder_from_payload(payload: Metadata) -> SourceFolder:
    return SourceFolder(
        tenant=str(payload["tenant"]),
        folder_id=str(payload["folder_id"]),
        source_version=str(payload["source_version"]),
        name=str(payload.get("name") or ""),
        path=_optional_text(payload.get("path")),
        parent_folder_id=_optional_text(payload.get("parent_folder_id")),
        description=str(payload.get("description") or ""),
        metadata=_metadata_or_empty(payload.get("metadata")),
    )


def _document_chunk_from_payload(payload: Metadata) -> DocumentChunk:
    return DocumentChunk(
        tenant=str(payload["tenant"]),
        document_type=str(payload["document_type"]),
        document_id=str(payload["document_id"]),
        source_version=str(payload["source_version"]),
        chunk_id=str(payload["chunk_id"]),
        chunk_index=int(str(payload["chunk_index"])),
        chunking_version=str(payload["chunking_version"]),
        text=str(payload["text"]),
        text_hash=str(payload["text_hash"]),
        start_offset=int(str(payload["start_offset"])),
        end_offset=int(str(payload["end_offset"])),
        embedding_model=str(payload["embedding_model"]),
        embedding_version=str(payload["embedding_version"]),
        index_schema_version=str(payload["index_schema_version"]),
        metadata=_metadata_or_empty(payload.get("metadata")),
    )


def _document_chunks_from_payload(value: object) -> tuple[DocumentChunk, ...]:
    return tuple(_document_chunk_from_payload(chunk) for chunk in _metadata_items(value))


def _document_profile_from_payload(payload: Metadata) -> DocumentProfile:
    return DocumentProfile(
        tenant=str(payload["tenant"]),
        document_type=str(payload["document_type"]),
        document_id=str(payload["document_id"]),
        source_version=str(payload["source_version"]),
        title=str(payload["title"]),
        summary=str(payload["summary"]),
        profile_version=str(payload["profile_version"]),
        profile_schema_version=str(payload["profile_schema_version"]),
        concepts=tuple(
            _profile_concept_from_payload(item)
            for item in _metadata_items(payload.get("concepts"))
        ),
        profile_confidence=_optional_float(payload.get("profile_confidence")),
        model=str(payload.get("model") or ""),
        prompt_version=str(payload.get("prompt_version") or ""),
        metadata=_metadata_or_empty(payload.get("metadata")),
    )


def _profile_concept_from_payload(payload: Metadata) -> ProfileConcept:
    return ProfileConcept(
        concept_id=str(payload["concept_id"]),
        concept_key=str(payload["concept_key"]),
        label=str(payload["label"]),
        confidence=_optional_float(payload.get("confidence")),
        evidence_chunk_ids=_string_tuple(payload.get("evidence_chunk_ids")),
        metadata=_metadata_or_empty(payload.get("metadata")),
    )


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item) for item in value)


def _nested_metadata(payload: Metadata, name: str) -> Metadata:
    return _metadata_or_empty(payload.get(name))


def _metadata_items(value: object) -> tuple[Metadata, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(_metadata_or_empty(item) for item in value if isinstance(item, dict))


def _metadata_or_empty(value: object) -> Metadata:
    return cast(Metadata, dict(value) if isinstance(value, dict) else {})


def _optional_text(value: object) -> str | None:
    return str(value) if value is not None else None


def _optional_float(value: object) -> float | None:
    return float(str(value)) if value is not None else None


def _optional_int(value: object) -> int | None:
    return int(str(value)) if value is not None else None
