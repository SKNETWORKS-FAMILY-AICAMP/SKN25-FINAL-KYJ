from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from foldmind_ai_core.core.domain.services.outbox import validate_outbox_event_fields
from foldmind_ai_core.shared.canonical_json import canonical_json
from foldmind_ai_core.shared.internal_ids import new_internal_id, stable_internal_id
from foldmind_ai_core.shared.types import JsonObject

OUTBOX_PAYLOAD_SCHEMA_VERSION = 1


class OutboxSourceKind(StrEnum):
    DOCUMENT = "document"
    FOLDER = "folder"


class OutboxEventType(StrEnum):
    DOCUMENT_INDEXED = "DOCUMENT_INDEXED"
    DOCUMENT_DELETED = "DOCUMENT_DELETED"
    DOCUMENT_FOLDER_RELATIONS_INDEXED = "DOCUMENT_FOLDER_RELATIONS_INDEXED"
    FOLDER_INDEXED = "FOLDER_INDEXED"
    FOLDER_SIGNALS_INVALIDATED = "FOLDER_SIGNALS_INVALIDATED"
    FOLDER_SIGNALS_INDEXED = "FOLDER_SIGNALS_INDEXED"
    FOLDER_DELETED = "FOLDER_DELETED"


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    tenant: str
    source_kind: str
    source_id: str
    event_type: str
    payload: JsonObject
    event_sequence: int | None = None
    payload_schema_version: int = OUTBOX_PAYLOAD_SCHEMA_VERSION
    idempotency_key: str = ""
    event_id: str = field(default_factory=new_internal_id)

    def __post_init__(self) -> None:
        if not self.idempotency_key.strip():
            object.__setattr__(
                self,
                "idempotency_key",
                stable_internal_id(
                    "outbox-event",
                    self.tenant,
                    self.source_kind,
                    self.source_id,
                    self.event_type,
                    canonical_json(self.payload),
                ),
            )
        validate_outbox_event_fields(
            tenant=self.tenant,
            source_kind=self.source_kind,
            source_id=self.source_id,
            event_type=self.event_type,
            event_sequence=self.event_sequence,
            payload_schema_version=self.payload_schema_version,
            expected_payload_schema_version=OUTBOX_PAYLOAD_SCHEMA_VERSION,
            idempotency_key=self.idempotency_key,
        )

    @property
    def partition_key(self) -> str:
        return f"{self.source_kind}:{self.tenant}:{self.source_id}"
