from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.shared.types import JsonObject


@dataclass(frozen=True, slots=True)
class PostgresOutboxEventRecord:
    event_id: str
    tenant: str
    source_kind: str
    source_id: str
    event_type: str
    payload_schema_version: int
    idempotency_key: str
    payload: JsonObject
