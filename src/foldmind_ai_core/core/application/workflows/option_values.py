from __future__ import annotations

from foldmind_ai_core.shared.types import JsonObject, Metadata

_MISSING = object()


def bool_option(
    options: JsonObject,
    name: str,
    *,
    default: bool = False,
) -> bool:
    value = options.get(name, _MISSING)
    if value is _MISSING:
        return default
    if isinstance(value, bool):
        return value
    raise TypeError(f"{name} option must be a boolean.")


def instruction_option(options: JsonObject) -> str:
    value = options.get("instruction", _MISSING)
    if value is _MISSING:
        raise ValueError("instruction option is required.")
    if not isinstance(value, str):
        raise TypeError("instruction option must be a string.")
    instruction = value.strip()
    if not instruction:
        raise ValueError("instruction option must not be blank.")
    return instruction


def optional_text_option(options: JsonObject, name: str) -> str | None:
    return optional_text_value(options.get(name), name=f"{name} option")


def optional_text_value(value: object, *, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    stripped = value.strip()
    return stripped or None


def string_value(value: object, *, name: str, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    raise TypeError(f"{name} option must be a string.")


def normalized_string_value(value: object, *, name: str, default: str) -> str:
    normalized = string_value(value, name=name, default=default).strip()
    return normalized or default


def string_tuple(value: object, *, name: str = "value") -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        stripped = value.strip()
        return (stripped,) if stripped else ()
    if isinstance(value, list | tuple):
        values: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError(f"{name} must contain strings.")
            stripped = item.strip()
            if stripped:
                values.append(stripped)
        return tuple(values)
    raise TypeError(f"{name} must be a string or sequence of strings.")


def non_blank_string_tuple(value: object, *, name: str = "value") -> tuple[str, ...]:
    if isinstance(value, str):
        raw_values = (value,)
    elif isinstance(value, list | tuple):
        raw_values = tuple(value)
    else:
        raise TypeError(f"{name} must be a string or sequence of strings.")

    values: list[str] = []
    for item in raw_values:
        if not isinstance(item, str) or not item.strip():
            raise TypeError(f"{name} must contain non-blank strings.")
        values.append(item.strip())
    return tuple(values)


def optional_string_tuple(value: object, *, name: str = "value") -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return (stripped,) if stripped else None
    return string_tuple(value, name=name)


def positive_int_option(options: JsonObject, name: str, *, default: int) -> int:
    return positive_int_value(options.get(name, _MISSING), name=name, default=default)


def positive_int_value(value: object, *, name: str, default: int) -> int:
    if value is _MISSING:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} option must be a positive integer.")
    if value <= 0:
        raise ValueError(f"{name} option must be positive.")
    return value


def metadata_option(options: JsonObject, name: str = "metadata") -> Metadata:
    value = options.get(name)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"{name} option must be an object.")
    return dict(value)
