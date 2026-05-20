from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import cast

from foldmind_ai_core.core.domain.models.indexing.outbox import (
    OUTBOX_PAYLOAD_SCHEMA_VERSION,
    OutboxEvent,
    OutboxEventType,
    OutboxSourceKind,
)
from foldmind_ai_core.adapters.inbound.messaging.projection_events import (
    DocumentDeletedProjectionEvent,
    DocumentFolderRelationsIndexedProjectionEvent,
    DocumentIndexedProjectionEvent,
    FolderDeletedProjectionEvent,
    FolderIndexedProjectionEvent,
)
from foldmind_ai_core.core.application.models.projection_inputs import (
    ProjectionDocument,
    ProjectionDocumentFolderRelationSnapshot,
    ProjectionDocumentProfile,
    ProjectionDocumentSignal,
    ProjectionFolder,
    ProjectionFolderSignal,
    ProjectionSignalEvidence,
)
from foldmind_ai_core.core.application.projections.vector import DocumentChunkVectorProjection
from foldmind_ai_core.shared.types import JsonObject, Metadata


def outbox_event_from_flattened_payload(
    value: bytes | str | Mapping[str, object],
) -> OutboxEvent:
    outbox_record = _json_object(value)
    partition_key = _required_text(outbox_record, "partition_key")
    event = OutboxEvent(
        event_id=_required_text(outbox_record, "event_id"),
        tenant=_required_text(outbox_record, "tenant_id"),
        source_kind=_required_text(outbox_record, "source_kind"),
        source_id=_required_text(outbox_record, "source_id"),
        event_type=_required_text(outbox_record, "event_type"),
        event_sequence=_optional_int(outbox_record.get("event_sequence")),
        payload_schema_version=_payload_schema_version(outbox_record),
        idempotency_key=_required_text(outbox_record, "idempotency_key"),
        payload=_json_object(_required_field(outbox_record, "payload")),
    )
    _validate_partition_key(partition_key, event)
    return event


def document_indexed_event_from_outbox(
    event: OutboxEvent,
) -> DocumentIndexedProjectionEvent:
    _require_event_type(event, OutboxEventType.DOCUMENT_INDEXED)
    _require_source_kind(event, OutboxSourceKind.DOCUMENT)
    payload = event.payload
    projection_event = DocumentIndexedProjectionEvent(
        document=_source_document_from_payload(
            _nested_json_object(payload, "source_document")
        ),
        chunks=_document_chunks_from_payload(payload.get("chunks")),
        profile=_document_profile_from_payload(_nested_json_object(payload, "profile")),
        signals=_document_signals_from_payload(payload.get("signals")),
    )
    _validate_document_indexed_event(projection_event)
    _validate_tenant(event, projection_event.document.tenant)
    _validate_source_id(
        event,
        projection_event.document.document_id,
    )
    return projection_event


def document_folder_relations_indexed_event_from_outbox(
    event: OutboxEvent,
) -> DocumentFolderRelationsIndexedProjectionEvent:
    _require_event_type(event, OutboxEventType.DOCUMENT_FOLDER_RELATIONS_INDEXED)
    _require_source_kind(event, OutboxSourceKind.DOCUMENT)
    snapshot = _folder_relation_snapshot_from_payload(
        _nested_json_object(event.payload, "folder_relation_snapshot")
    )
    _validate_tenant(event, snapshot.tenant)
    _validate_source_id(event, snapshot.document_id)
    return DocumentFolderRelationsIndexedProjectionEvent(
        folder_relation_snapshot=snapshot,
    )


def document_deleted_event_from_outbox(
    event: OutboxEvent,
) -> DocumentDeletedProjectionEvent:
    _require_event_type(event, OutboxEventType.DOCUMENT_DELETED)
    _require_source_kind(event, OutboxSourceKind.DOCUMENT)
    document_id = _required_text(event.payload, "document_id")
    tenant = _required_text(event.payload, "tenant")
    _validate_tenant(event, tenant)
    _validate_source_id(event, document_id)
    return DocumentDeletedProjectionEvent(
        document_id=document_id,
        affected_folder_ids=_string_tuple(event.payload, "affected_folder_ids"),
    )


def folder_indexed_event_from_outbox(
    event: OutboxEvent,
) -> FolderIndexedProjectionEvent:
    _require_event_type(event, OutboxEventType.FOLDER_INDEXED)
    _require_source_kind(event, OutboxSourceKind.FOLDER)
    projection_event = FolderIndexedProjectionEvent(
        folder=_source_folder_from_payload(
            _nested_json_object(event.payload, "source_folder")
        ),
        signals=_folder_signals_from_payload(event.payload.get("signals")),
    )
    _validate_tenant(event, projection_event.folder.tenant)
    _validate_source_id(event, projection_event.folder.folder_id)
    return projection_event


def folder_deleted_event_from_outbox(
    event: OutboxEvent,
) -> FolderDeletedProjectionEvent:
    _require_event_type(event, OutboxEventType.FOLDER_DELETED)
    _require_source_kind(event, OutboxSourceKind.FOLDER)
    folder_id = _required_text(event.payload, "folder_id")
    tenant = _required_text(event.payload, "tenant")
    _validate_tenant(event, tenant)
    _validate_source_id(event, folder_id)
    return FolderDeletedProjectionEvent(
        folder_id=folder_id,
    )


def _require_event_type(event: OutboxEvent, expected: OutboxEventType) -> None:
    actual = OutboxEventType(event.event_type)
    if actual != expected:
        raise ValueError(f"Expected {expected}, got {actual}.")


def _require_source_kind(event: OutboxEvent, expected: OutboxSourceKind) -> None:
    actual = OutboxSourceKind(event.source_kind)
    if actual != expected:
        raise ValueError(f"Expected source {expected}, got {actual}.")


def _validate_source_id(event: OutboxEvent, payload_id: str) -> None:
    if event.source_id != payload_id:
        raise ValueError(
            "Outbox message source_id does not match projection payload identity."
        )


def _validate_tenant(event: OutboxEvent, payload_tenant: str) -> None:
    if event.tenant != payload_tenant:
        raise ValueError(
            "Outbox message tenant does not match projection payload tenant."
        )


def _validate_partition_key(partition_key: str, event: OutboxEvent) -> None:
    if partition_key != event.partition_key:
        raise ValueError(
            "Outbox message partition_key "
            f"{partition_key!s} does not match {event.partition_key}."
        )


def _validate_document_indexed_event(event: DocumentIndexedProjectionEvent) -> None:
    expected_context = (
        event.document.tenant,
        event.document.document_id,
        event.document.source_version,
        event.document.content_digest,
    )
    profile_context = (
        event.profile.tenant,
        event.profile.document_id,
        event.profile.source_version,
        event.profile.content_digest,
    )
    if (
        profile_context != expected_context
        or any(
            (
                chunk.tenant,
                chunk.document_id,
                chunk.source_version,
                chunk.content_digest,
            )
            != expected_context
            for chunk in event.chunks
        )
        or any(
            (
                signal.tenant,
                signal.document_id,
                signal.source_version,
                signal.content_digest,
            )
            != expected_context
            for signal in event.signals
        )
    ):
        raise ValueError(
            "Outbox document indexed payload contains mismatched document projection context."
        )
def _json_object(value: object) -> JsonObject:
    if isinstance(value, Mapping):
        return cast(JsonObject, dict(value))
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, Mapping):
            return cast(JsonObject, dict(parsed))
    raise ValueError("Outbox message value must be a JSON object.")


def _required_field(record: Mapping[str, object], name: str) -> object:
    value = record.get(name)
    if value is None:
        raise ValueError(f"Outbox message is missing required field: {name}.")
    return value


def _required_text(record: Mapping[str, object], name: str) -> str:
    value = _required_field(record, name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Outbox message field must be a non-empty string: {name}.")
    return value.strip()


def _payload_schema_version(record: Mapping[str, object]) -> int:
    version = _required_int(record, "payload_schema_version")
    if version != OUTBOX_PAYLOAD_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported outbox message payload schema version: {version}."
        )
    return version


def _source_document_from_payload(payload: JsonObject) -> ProjectionDocument:
    return ProjectionDocument(
        tenant=_required_text(payload, "tenant"),
        document_type=_optional_non_blank_text(
            payload.get("document_type"),
            "document_type",
        ),
        document_id=_required_text(payload, "document_id"),
        source_version=_required_text(payload, "source_version"),
        content_digest=_required_text(payload, "content_digest"),
        content_size_bytes=_required_non_negative_int(payload, "content_size_bytes"),
        created_at=_required_text(payload, "created_at"),
        updated_at=_required_text(payload, "updated_at"),
        title=_optional_content_text(payload.get("title")) or "",
        metadata=_metadata(payload, "metadata"),
    )


def _folder_relation_snapshot_from_payload(
    payload: JsonObject,
) -> ProjectionDocumentFolderRelationSnapshot:
    return ProjectionDocumentFolderRelationSnapshot(
        tenant=_required_text(payload, "tenant"),
        document_id=_required_text(payload, "document_id"),
        source_version=_required_text(payload, "source_version"),
        folder_ids=_string_tuple(payload, "folder_ids"),
    )


def _source_folder_from_payload(payload: JsonObject) -> ProjectionFolder:
    return ProjectionFolder(
        tenant=_required_text(payload, "tenant"),
        folder_id=_required_text(payload, "folder_id"),
        source_version=_required_text(payload, "source_version"),
        name=_required_content_text(payload, "name"),
        created_at=_required_text(payload, "created_at"),
        updated_at=_required_text(payload, "updated_at"),
        path=_optional_content_text(payload.get("path")),
        parent_folder_id=_optional_non_blank_text(
            payload.get("parent_folder_id"),
            "parent_folder_id",
        ),
        description=_optional_content_text(payload.get("description")) or "",
        metadata=_metadata(payload, "metadata"),
    )


def _document_chunk_from_payload(payload: JsonObject) -> DocumentChunkVectorProjection:
    return DocumentChunkVectorProjection(
        tenant=_required_text(payload, "tenant"),
        document_type=_optional_non_blank_text(
            payload.get("document_type"),
            "document_type",
        ),
        document_id=_required_text(payload, "document_id"),
        source_version=_required_text(payload, "source_version"),
        content_digest=_required_text(payload, "content_digest"),
        created_at=_required_text(payload, "created_at"),
        updated_at=_required_text(payload, "updated_at"),
        chunk_id=_required_text(payload, "chunk_id"),
        chunk_index=_required_int(payload, "chunk_index"),
        chunking_version=_required_text(payload, "chunking_version"),
        text=_required_content_text(payload, "text"),
        text_hash=_required_text(payload, "text_hash"),
        start_offset=_required_int(payload, "start_offset"),
        end_offset=_required_int(payload, "end_offset"),
        embedding_model=_required_text(payload, "embedding_model"),
        embedding_version=_required_text(payload, "embedding_version"),
        index_schema_version=_required_text(payload, "index_schema_version"),
        metadata=_metadata(payload, "metadata"),
    )


def _document_chunks_from_payload(
    value: object,
) -> tuple[DocumentChunkVectorProjection, ...]:
    return tuple(
        _document_chunk_from_payload(chunk)
        for chunk in _json_object_items(value, "chunks")
    )


def _document_profile_from_payload(payload: JsonObject) -> ProjectionDocumentProfile:
    return ProjectionDocumentProfile(
        tenant=_required_text(payload, "tenant"),
        document_type=_optional_non_blank_text(
            payload.get("document_type"),
            "document_type",
        ),
        document_id=_required_text(payload, "document_id"),
        source_version=_required_text(payload, "source_version"),
        content_digest=_required_text(payload, "content_digest"),
        created_at=_required_text(payload, "created_at"),
        updated_at=_required_text(payload, "updated_at"),
        title=_required_content_text(payload, "title"),
        signal_set_version=_required_text(payload, "signal_set_version"),
        model=_optional_text(payload.get("model")) or "",
        metadata=_metadata(payload, "metadata"),
    )


def _document_signal_from_payload(payload: JsonObject) -> ProjectionDocumentSignal:
    return ProjectionDocumentSignal(
        signal_id=_required_text(payload, "signal_id"),
        tenant=_required_text(payload, "tenant"),
        document_type=_optional_non_blank_text(
            payload.get("document_type"),
            "document_type",
        ),
        document_id=_required_text(payload, "document_id"),
        source_version=_required_text(payload, "source_version"),
        content_digest=_required_text(payload, "content_digest"),
        signal_type=_required_text(payload, "signal_type"),
        signal_key=_required_text(payload, "signal_key"),
        text=_required_content_text(payload, "text"),
        attributes=_metadata(payload, "attributes"),
        evidence=tuple(
            _signal_evidence_from_payload(item)
            for item in _json_object_items(payload.get("evidence"), "evidence")
        ),
        confidence=_optional_confidence(payload.get("confidence")),
        extractor_name=_required_text(payload, "extractor_name"),
        extractor_version=_required_text(payload, "extractor_version"),
        metadata=_metadata(payload, "metadata"),
    )


def _document_signals_from_payload(
    value: object,
) -> tuple[ProjectionDocumentSignal, ...]:
    return tuple(
        _document_signal_from_payload(signal)
        for signal in _json_object_items(value, "signals")
    )


def _folder_signal_from_payload(payload: JsonObject) -> ProjectionFolderSignal:
    return ProjectionFolderSignal(
        signal_id=_required_text(payload, "signal_id"),
        tenant=_required_text(payload, "tenant"),
        folder_id=_required_text(payload, "folder_id"),
        source_version=_required_text(payload, "source_version"),
        signal_type=_required_text(payload, "signal_type"),
        signal_key=_required_text(payload, "signal_key"),
        text=_required_content_text(payload, "text"),
        related_document_id=_optional_non_blank_text(
            payload.get("related_document_id"),
            "related_document_id",
        ),
        attributes=_metadata(payload, "attributes"),
        evidence=tuple(
            cast(Metadata, dict(item))
            for item in _json_object_items(payload.get("evidence"), "evidence")
        ),
        confidence=_optional_confidence(payload.get("confidence")),
        extractor_name=_required_text(payload, "extractor_name"),
        extractor_version=_required_text(payload, "extractor_version"),
        metadata=_metadata(payload, "metadata"),
    )


def _folder_signals_from_payload(value: object) -> tuple[ProjectionFolderSignal, ...]:
    return tuple(
        _folder_signal_from_payload(signal)
        for signal in _optional_json_object_items(value, "signals")
    )


def _signal_evidence_from_payload(payload: JsonObject) -> ProjectionSignalEvidence:
    return ProjectionSignalEvidence(
        chunk_id=_required_text(payload, "chunk_id"),
        quote=_required_content_text(payload, "quote"),
        start_offset=_optional_int(payload.get("start_offset")),
        end_offset=_optional_int(payload.get("end_offset")),
        metadata=_metadata(payload, "metadata"),
    )


def _string_tuple(payload: Mapping[str, object], name: str) -> tuple[str, ...]:
    value = payload.get(name)
    if value is None:
        return ()
    if not isinstance(value, list | tuple) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(f"Outbox message field must be a list of strings: {name}.")
    stripped_values = tuple(cast(str, item).strip() for item in value)
    if not all(stripped_values):
        raise ValueError(f"Outbox message field must not contain blank strings: {name}.")
    return stripped_values


def _nested_json_object(payload: JsonObject, name: str) -> JsonObject:
    value = payload.get(name)
    if not isinstance(value, Mapping):
        raise ValueError(f"Outbox message field must be a JSON object: {name}.")
    return cast(JsonObject, dict(value))


def _json_object_items(value: object, name: str) -> tuple[JsonObject, ...]:
    if not isinstance(value, list | tuple) or not all(
        isinstance(item, Mapping) for item in value
    ):
        raise ValueError(f"Outbox message field must be a list of objects: {name}.")
    return tuple(cast(JsonObject, dict(item)) for item in value)


def _optional_json_object_items(value: object, name: str) -> tuple[JsonObject, ...]:
    if value is None:
        return ()
    return _json_object_items(value, name)


def _metadata(payload: Mapping[str, object], name: str) -> Metadata:
    value = payload.get(name)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"Outbox message field must be metadata object: {name}.")
    return cast(Metadata, dict(value))


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Outbox message optional text field must be a string.")
    stripped = value.strip()
    return stripped or None


def _required_content_text(record: Mapping[str, object], name: str) -> str:
    value = _required_field(record, name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Outbox message field must be a non-empty string: {name}.")
    return value


def _optional_content_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Outbox message optional text field must be a string.")
    return value


def _optional_non_blank_text(value: object, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Outbox message optional text field must be a non-empty string: {name}."
        )
    return value.strip()


def _optional_confidence(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("Outbox message confidence field must be numeric.")
    confidence = float(value)
    if not math.isfinite(confidence) or confidence < 0.0 or confidence > 1.0:
        raise ValueError("Outbox message confidence field must be between 0 and 1.")
    return confidence


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Outbox message optional int field must be an integer.")
    return value


def _required_int(payload: Mapping[str, object], name: str) -> int:
    value = _required_field(payload, name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Outbox message field must be an integer: {name}.")
    return value


def _required_non_negative_int(payload: Mapping[str, object], name: str) -> int:
    value = _required_int(payload, name)
    if value < 0:
        raise ValueError(f"Outbox message field must be non-negative: {name}.")
    return value
