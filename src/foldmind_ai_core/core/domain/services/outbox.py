from __future__ import annotations

from foldmind_ai_core.shared.validation import InvalidInputError


def validate_outbox_event_fields(
    *,
    tenant: str,
    source_kind: str,
    source_id: str,
    event_type: str,
    event_sequence: int | None,
    payload_schema_version: int,
    expected_payload_schema_version: int,
    idempotency_key: str,
) -> None:
    _require_non_blank(tenant, "tenant")
    _require_non_blank(source_kind, "source_kind")
    _require_non_blank(source_id, "source_id")
    _require_non_blank(event_type, "event_type")
    _require_non_blank(idempotency_key, "idempotency_key")
    if event_sequence is not None and (
        isinstance(event_sequence, bool)
        or not isinstance(event_sequence, int)
        or event_sequence <= 0
    ):
        raise InvalidInputError("outbox event_sequence must be a positive integer.")
    if (
        isinstance(payload_schema_version, bool)
        or not isinstance(payload_schema_version, int)
        or payload_schema_version != expected_payload_schema_version
    ):
        raise InvalidInputError(
            f"outbox payload schema version must be {expected_payload_schema_version}."
        )


def _require_non_blank(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError(f"{field_name} must not be blank.")
