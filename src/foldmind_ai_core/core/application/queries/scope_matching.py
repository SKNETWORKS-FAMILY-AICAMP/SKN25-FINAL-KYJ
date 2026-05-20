from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import TypeVar

from foldmind_ai_core.core.application.queries.retrieval import SearchScope, TimestampRange

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
    return sorted(
        results,
        key=lambda item: _timestamp_key(timestamp_value(item, scope.sort.field)),
        reverse=scope.sort.direction == "desc",
    )


def matches_timestamp_scope(
    *,
    created_at: str,
    updated_at: str,
    scope: SearchScope | None,
) -> bool:
    if scope is None:
        return True
    return _matches_timestamp_range(created_at, scope.created_at) and _matches_timestamp_range(
        updated_at,
        scope.updated_at,
    )


def _matches_timestamp_range(value: str, timestamp_range: TimestampRange | None) -> bool:
    if timestamp_range is None:
        return True
    timestamp = _timestamp_key(value)
    if timestamp_range.gt is not None and timestamp <= _timestamp_key(timestamp_range.gt):
        return False
    if timestamp_range.gte is not None and timestamp < _timestamp_key(timestamp_range.gte):
        return False
    if timestamp_range.lt is not None and timestamp >= _timestamp_key(timestamp_range.lt):
        return False
    if timestamp_range.lte is not None and timestamp > _timestamp_key(timestamp_range.lte):
        return False
    return True


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
