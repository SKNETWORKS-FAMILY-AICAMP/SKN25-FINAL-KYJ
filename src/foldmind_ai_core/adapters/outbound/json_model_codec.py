from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import fields, is_dataclass
from enum import StrEnum
from typing import Any, TypeVar, get_args, get_origin, get_type_hints

PostDecodeHook = Callable[[type[object], dict[str, object]], dict[str, object]]
T = TypeVar("T")


class JsonModelCodec:
    def __init__(
        self,
        *,
        models: Sequence[type[object]],
        type_key: str,
        value_key: str = "value",
        localns: Mapping[str, object] | None = None,
        post_decode: PostDecodeHook | None = None,
        label: str = "model",
    ) -> None:
        self._model_by_name = {model.__name__: model for model in models}
        self._type_key = type_key
        self._value_key = value_key
        self._localns = dict(localns or {})
        self._post_decode = post_decode
        self._label = label
        self._type_hints_cache: dict[type[object], dict[str, object]] = {}

    def encode(self, value: object) -> Any:
        if isinstance(value, StrEnum):
            return str(value)
        if value is None or isinstance(value, str | int | float | bool):
            return value
        if is_dataclass(value):
            return self._encode_model(value)
        if isinstance(value, tuple | list):
            return [self.encode(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self.encode(item) for key, item in value.items()}
        raise TypeError(f"Unsupported {self._label} JSON value: {type(value).__name__}")

    def restore(self, value: object) -> object:
        if value is None or isinstance(value, str | int | float | bool):
            return value
        if isinstance(value, list):
            return [self.restore(item) for item in value]
        if isinstance(value, dict):
            if self._type_key in value and self._value_key in value:
                return self._decode_model(value)
            return {str(key): self.restore(item) for key, item in value.items()}
        raise TypeError(
            f"Unsupported {self._label} JSON payload value: {type(value).__name__}"
        )

    def restore_typed(self, value: object, expected_type: type[T]) -> T:
        restored = self.restore(value)
        if isinstance(restored, expected_type):
            return restored
        raise TypeError(
            f"Expected {self._label} JSON value {expected_type.__name__}, "
            f"got {type(restored).__name__}."
        )

    def _encode_model(self, value: object) -> dict[str, Any]:
        model_type = type(value)
        if self._model_by_name.get(model_type.__name__) is not model_type:
            raise TypeError(f"Unsupported {self._label} JSON type: {model_type.__name__}")
        return {
            self._type_key: model_type.__name__,
            self._value_key: {
                field.name: self.encode(getattr(value, field.name))
                for field in fields(value)
            },
        }

    def _decode_model(self, value: Mapping[str, Any]) -> object:
        model_type = self._decode_model_type(value)
        raw_data = value.get(self._value_key)
        if not isinstance(raw_data, dict):
            raise TypeError(f"{self._label.capitalize()} JSON value must be a dictionary.")

        hints = self._type_hints(model_type)
        restored = {
            key: self._coerce_field(self.restore(item), hints.get(key))
            for key, item in raw_data.items()
        }
        if self._post_decode is not None:
            restored = self._post_decode(model_type, restored)
        return model_type(**restored)

    def _decode_model_type(self, value: Mapping[str, Any]) -> type[object]:
        type_id = value.get(self._type_key)
        if not isinstance(type_id, str):
            raise TypeError(f"{self._label.capitalize()} JSON type must be a string.")
        model_type = self._model_by_name.get(type_id)
        if model_type is None:
            raise TypeError(f"Unsupported {self._label} JSON type: {type_id}")
        return model_type

    @staticmethod
    def _coerce_field(value: object, annotation: object | None) -> object:
        if annotation is None:
            return value
        if get_origin(annotation) is tuple and isinstance(value, list):
            return tuple(value)
        enum_type = _enum_type(annotation)
        if enum_type is not None and isinstance(value, str):
            return enum_type(value)
        return value

    def _type_hints(self, model_type: type[object]) -> dict[str, object]:
        hints = self._type_hints_cache.get(model_type)
        if hints is None:
            hints = get_type_hints(model_type, localns=self._localns)
            self._type_hints_cache[model_type] = hints
        return hints


def _enum_type(annotation: object) -> type[StrEnum] | None:
    if isinstance(annotation, type) and issubclass(annotation, StrEnum):
        return annotation
    for arg in get_args(annotation):
        if isinstance(arg, type) and issubclass(arg, StrEnum):
            return arg
    return None
