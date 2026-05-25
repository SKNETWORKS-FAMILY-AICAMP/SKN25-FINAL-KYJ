from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import TypeVar

from foldmind_ai_core.core.application.models.search import SearchScope

_T = TypeVar("_T")
_MIN_TIMESTAMP = datetime.min.replace(tzinfo=UTC)


def sort_by_timestamp_scope(
    items: Iterable[_T],
    *,
    scope: SearchScope | None,
    timestamp_value: Callable[[_T, str], str],
) -> list[_T]:
    results = list(items)
    if scope is None or scope.sort is None:
        return results
    sort = scope.sort
    return sorted(
        results,
        key=lambda item: _timestamp_key(timestamp_value(item, sort.field)),
        reverse=sort.direction == "desc",
    )


def matches_timestamp_scope(
    *,
    created_at: str,
    updated_at: str,
    scope: SearchScope | None,
) -> bool:
    if scope is None:
        return True
    return _matches_timestamp(created_at, scope.created_at) and _matches_timestamp(
        updated_at,
        scope.updated_at,
    )


def _matches_timestamp(value: str, expected: datetime | None) -> bool:
    if expected is None:
        return True
    return _timestamp_key(value) == expected.astimezone(UTC)


def _timestamp_key(value: str) -> datetime:
    if not value:
        return _MIN_TIMESTAMP
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return _MIN_TIMESTAMP
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return _MIN_TIMESTAMP
    return parsed.astimezone(UTC)
