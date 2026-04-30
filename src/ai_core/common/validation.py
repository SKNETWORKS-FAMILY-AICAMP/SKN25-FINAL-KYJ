from __future__ import annotations

from collections.abc import Iterable


class InvalidInputError(ValueError):
    """Raised when an application command violates required input rules."""


def require_non_blank(value: str, field_name: str) -> None:
    if not value.strip():
        raise InvalidInputError(f"{field_name} must not be blank.")


def require_optional_non_blank(value: str | None, field_name: str) -> None:
    if value is not None:
        require_non_blank(value, field_name)


def require_non_blank_items(values: Iterable[str], field_name: str) -> None:
    for index, value in enumerate(values):
        require_non_blank(value, f"{field_name}[{index}]")
