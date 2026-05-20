from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID


class InvalidInputError(ValueError):
    """Raised when an application command violates required input rules."""


def require_non_blank(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise InvalidInputError(f"{field_name} must not be blank.")
    return normalized


def require_optional_non_blank(value: str | None, field_name: str) -> str | None:
    if value is not None:
        return require_non_blank(value, field_name)
    return None


def require_uuid(value: str, field_name: str) -> str:
    normalized = require_non_blank(value, field_name)
    try:
        UUID(normalized)
    except ValueError as exc:
        raise InvalidInputError(f"{field_name} must be a UUID.") from exc
    return normalized


def require_optional_uuid(value: str | None, field_name: str) -> str | None:
    if value is not None:
        return require_uuid(value, field_name)
    return None


def require_uuid_items(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    return tuple(
        require_uuid(value, f"{field_name}[{index}]")
        for index, value in enumerate(values)
    )


def require_aware_iso_timestamp(value: str, field_name: str) -> str:
    timestamp = _parse_iso_timestamp(require_non_blank(value, field_name), field_name)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise InvalidInputError(f"{field_name} must include a timezone offset.")
    return timestamp.isoformat()


def resolve_requested_at(value: str | None) -> str:
    if value is None:
        return _current_utc_timestamp()
    timestamp = _parse_iso_timestamp(
        require_non_blank(value, "requested_at"),
        "requested_at",
    )
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        return _current_utc_timestamp()
    return timestamp.isoformat()


def _parse_iso_timestamp(value: str, field_name: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidInputError(f"{field_name} must be an ISO timestamp.") from exc


def _current_utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()
