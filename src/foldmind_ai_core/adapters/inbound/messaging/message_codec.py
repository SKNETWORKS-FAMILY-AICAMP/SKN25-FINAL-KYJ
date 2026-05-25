from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import cast

from foldmind_ai_core.core.application.models.projection_commands import (
    DeleteDocumentProjectionCommand,
    DeleteFolderProjectionCommand,
    InvalidateFolderSignalsCommand,
    ProjectDocumentCommand,
    ProjectDocumentFolderRelationsCommand,
    ProjectFolderCommand,
    ProjectFolderSignalsCommand,
)
from foldmind_ai_core.core.application.models.vector_projection import DocumentChunkVectorProjection
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.outbox import (
    OUTBOX_PAYLOAD_SCHEMA_VERSION,
    OutboxEvent,
    OutboxEventType,
    OutboxSourceKind,
)
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
    DocumentSignalEvidence,
    DocumentSignalType,
)
from foldmind_ai_core.core.domain.models.document_sources import DocumentSourceState
from foldmind_ai_core.core.domain.models.folder_signals import (
    FolderSignal,
    FolderSignalType,
)
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
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


def project_document_command_from_outbox(
    event: OutboxEvent,
) -> ProjectDocumentCommand:
    _require_event_type(event, OutboxEventType.DOCUMENT_INDEXED)
    _require_source_kind(event, OutboxSourceKind.DOCUMENT)
    payload = event.payload
    document_index_payload = _nested_json_object(payload, "profile")
    command = ProjectDocumentCommand(
        document=_source_document_from_payload(
            _nested_json_object(payload, "source_document")
        ),
        chunks=_document_chunks_from_payload(payload.get("chunks")),
        document_index=_document_index_from_payload(document_index_payload),
        signals=_document_signals_from_payload(payload.get("signals")),
    )
    _validate_document_indexed_command(command, document_index_payload)
    _validate_tenant(event, command.document.tenant)
    _validate_source_id(
        event,
        command.document.document_id,
    )
    return command


def project_document_folder_relations_command_from_outbox(
    event: OutboxEvent,
) -> ProjectDocumentFolderRelationsCommand:
    _require_event_type(event, OutboxEventType.DOCUMENT_FOLDER_RELATIONS_INDEXED)
    _require_source_kind(event, OutboxSourceKind.DOCUMENT)
    snapshot = _folder_relation_snapshot_from_payload(
        _nested_json_object(event.payload, "folder_relation_snapshot")
    )
    _validate_tenant(event, snapshot.tenant)
    _validate_source_id(event, snapshot.document_id)
    return ProjectDocumentFolderRelationsCommand(
        folder_relation_snapshot=snapshot,
    )


def delete_document_projection_command_from_outbox(
    event: OutboxEvent,
) -> DeleteDocumentProjectionCommand:
    _require_event_type(event, OutboxEventType.DOCUMENT_DELETED)
    _require_source_kind(event, OutboxSourceKind.DOCUMENT)
    document_id = _required_text(event.payload, "document_id")
    tenant = _required_text(event.payload, "tenant")
    _validate_tenant(event, tenant)
    _validate_source_id(event, document_id)
    return DeleteDocumentProjectionCommand(
        tenant=tenant,
        document_id=document_id,
        affected_folder_ids=_string_tuple(event.payload, "affected_folder_ids"),
    )


def project_folder_command_from_outbox(
    event: OutboxEvent,
) -> ProjectFolderCommand:
    _require_event_type(event, OutboxEventType.FOLDER_INDEXED)
    _require_source_kind(event, OutboxSourceKind.FOLDER)
    command = ProjectFolderCommand(
        folder=_source_folder_from_payload(
            _nested_json_object(event.payload, "source_folder")
        ),
    )
    _validate_tenant(event, command.folder.tenant)
    _validate_source_id(event, command.folder.folder_id)
    return command


def project_folder_signals_command_from_outbox(
    event: OutboxEvent,
) -> ProjectFolderSignalsCommand:
    _require_event_type(event, OutboxEventType.FOLDER_SIGNALS_INDEXED)
    _require_source_kind(event, OutboxSourceKind.FOLDER)
    command = ProjectFolderSignalsCommand(
        folder=_source_folder_from_payload(
            _nested_json_object(event.payload, "source_folder")
        ),
        folder_signal_input_digest=_required_text(
            event.payload,
            "folder_signal_input_digest",
        ),
        signal_generation_version=_required_text(
            event.payload,
            "signal_generation_version",
        ),
        signals=_folder_signals_from_payload(event.payload.get("signals")),
    )
    _validate_tenant(event, command.folder.tenant)
    _validate_source_id(event, command.folder.folder_id)
    return command


def invalidate_folder_signals_command_from_outbox(
    event: OutboxEvent,
) -> InvalidateFolderSignalsCommand:
    _require_event_type(event, OutboxEventType.FOLDER_SIGNALS_INVALIDATED)
    _require_source_kind(event, OutboxSourceKind.FOLDER)
    tenant = _required_text(event.payload, "tenant")
    folder_id = _required_text(event.payload, "folder_id")
    _validate_tenant(event, tenant)
    _validate_source_id(event, folder_id)
    return InvalidateFolderSignalsCommand(
        tenant=tenant,
        folder_id=folder_id,
        folder_signal_input_digest=_required_text(
            event.payload,
            "folder_signal_input_digest",
        ),
    )


def delete_folder_projection_command_from_outbox(
    event: OutboxEvent,
) -> DeleteFolderProjectionCommand:
    _require_event_type(event, OutboxEventType.FOLDER_DELETED)
    _require_source_kind(event, OutboxSourceKind.FOLDER)
    folder_id = _required_text(event.payload, "folder_id")
    tenant = _required_text(event.payload, "tenant")
    _validate_tenant(event, tenant)
    _validate_source_id(event, folder_id)
    return DeleteFolderProjectionCommand(
        tenant=tenant,
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


def _validate_document_indexed_command(
    command: ProjectDocumentCommand,
    document_index_payload: JsonObject,
) -> None:
    expected_context = (
        command.document.tenant,
        command.document.document_id,
        command.document.source_version,
        command.document.content_digest,
        command.document_index.document_index_input_digest,
        command.document_index.document_signal_input_digest,
    )
    document_index_context = (
        _required_text(document_index_payload, "tenant"),
        command.document_index.document_id,
        _required_text(document_index_payload, "source_version"),
        _required_text(document_index_payload, "content_digest"),
        command.document_index.document_index_input_digest,
        command.document_index.document_signal_input_digest,
    )
    if (
        document_index_context != expected_context
        or any(
            (
                chunk.tenant,
                chunk.document_id,
                chunk.source_version,
                chunk.content_digest,
                chunk.source_input_digest,
                command.document_index.document_signal_input_digest,
            )
            != expected_context
            for chunk in command.chunks
        )
        or any(
            (
                signal.tenant,
                signal.document_id,
                signal.source_version,
                command.document.content_digest,
                command.document_index.document_index_input_digest,
                signal.document_signal_input_digest,
            )
            != expected_context
            for signal in command.signals
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


def _source_document_from_payload(payload: JsonObject) -> DocumentSourceState:
    return DocumentSourceState(
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
) -> SourceDocumentFolderRelationSnapshot:
    return SourceDocumentFolderRelationSnapshot(
        tenant=_required_text(payload, "tenant"),
        document_id=_required_text(payload, "document_id"),
        source_version=_required_text(payload, "source_version"),
        folder_ids=_string_tuple(payload, "folder_ids"),
    )


def _source_folder_from_payload(payload: JsonObject) -> SourceFolder:
    return SourceFolder(
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
    search_text = _required_content_text(payload, "search_text")
    return DocumentChunkVectorProjection(
        tenant=_required_text(payload, "tenant"),
        document_type=_optional_non_blank_text(
            payload.get("document_type"),
            "document_type",
        ),
        document_id=_required_text(payload, "document_id"),
        source_version=_required_text(payload, "source_version"),
        content_digest=_required_text(payload, "content_digest"),
        source_input_digest=_required_text(payload, "source_input_digest"),
        vector_input_digest=_required_text(payload, "vector_input_digest"),
        created_at=_required_text(payload, "created_at"),
        updated_at=_required_text(payload, "updated_at"),
        chunk_id=_required_text(payload, "chunk_id"),
        chunk_index=_required_int(payload, "chunk_index"),
        text=search_text,
        text_hash=hashlib.sha256(search_text.encode("utf-8")).hexdigest(),
        start_offset=_required_int(payload, "source_start_offset"),
        end_offset=_required_int(payload, "source_end_offset"),
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


def _document_index_from_payload(payload: JsonObject) -> DocumentIndexState:
    _required_text(payload, "tenant")
    _optional_non_blank_text(payload.get("document_type"), "document_type")
    _required_text(payload, "source_version")
    _required_text(payload, "content_digest")
    _required_text(payload, "created_at")
    _required_text(payload, "updated_at")
    _required_content_text(payload, "title")
    _metadata(payload, "metadata")
    return DocumentIndexState(
        document_id=_required_text(payload, "document_id"),
        document_index_input_digest=_required_text(
            payload,
            "document_index_input_digest",
        ),
        document_signal_input_digest=_required_text(
            payload,
            "document_signal_input_digest",
        ),
        signal_generation_version=_required_text(payload, "signal_generation_version"),
    )


def _document_signal_from_payload(payload: JsonObject) -> DocumentSignal:
    _required_text(payload, "content_digest")
    return DocumentSignal(
        signal_id=_required_text(payload, "signal_id"),
        tenant=_required_text(payload, "tenant"),
        document_type=_optional_non_blank_text(
            payload.get("document_type"),
            "document_type",
        ),
        document_id=_required_text(payload, "document_id"),
        source_version=_required_text(payload, "source_version"),
        document_signal_input_digest=_required_text(
            payload,
            "document_signal_input_digest",
        ),
        signal_generation_version=_required_text(
            payload,
            "signal_generation_version",
        ),
        signal_type=DocumentSignalType(_required_text(payload, "signal_type")),
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
        generation_model=_optional_text(payload.get("generation_model")),
        metadata=_metadata(payload, "metadata"),
    )


def _document_signals_from_payload(
    value: object,
) -> tuple[DocumentSignal, ...]:
    return tuple(
        _document_signal_from_payload(signal)
        for signal in _json_object_items(value, "signals")
    )


def _folder_signal_from_payload(payload: JsonObject) -> FolderSignal:
    return FolderSignal(
        signal_id=_required_text(payload, "signal_id"),
        tenant=_required_text(payload, "tenant"),
        folder_id=_required_text(payload, "folder_id"),
        source_version=_required_text(payload, "source_version"),
        folder_signal_input_digest=_required_text(
            payload,
            "folder_signal_input_digest",
        ),
        signal_generation_version=_required_text(
            payload,
            "signal_generation_version",
        ),
        signal_type=FolderSignalType(_required_text(payload, "signal_type")),
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
        generation_model=_optional_text(payload.get("generation_model")),
        metadata=_metadata(payload, "metadata"),
    )


def _folder_signals_from_payload(value: object) -> tuple[FolderSignal, ...]:
    return tuple(
        _folder_signal_from_payload(signal)
        for signal in _optional_json_object_items(value, "signals")
    )


def _signal_evidence_from_payload(payload: JsonObject) -> DocumentSignalEvidence:
    return DocumentSignalEvidence(
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
