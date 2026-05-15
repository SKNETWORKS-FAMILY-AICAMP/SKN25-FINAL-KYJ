from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from foldmind_ai_core.shared.internal_ids import new_internal_id
from foldmind_ai_core.shared.types import Metadata


class OutboxAggregateType(StrEnum):
    DOCUMENT = "DOCUMENT"
    FOLDER = "FOLDER"


class OutboxEventType(StrEnum):
    DOCUMENT_INDEXED = "DOCUMENT_INDEXED"
    DOCUMENT_DELETED = "DOCUMENT_DELETED"
    FOLDER_INDEXED = "FOLDER_INDEXED"
    FOLDER_DELETED = "FOLDER_DELETED"


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: Metadata
    sequence: int | None = None
    event_schema_version: str = "1"
    id: str = field(default_factory=new_internal_id)

    @property
    def event_key(self) -> str:
        return f"{self.aggregate_type}:{self.aggregate_id}"
