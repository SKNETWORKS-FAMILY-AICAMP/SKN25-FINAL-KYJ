from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(frozen=True, slots=True)
class VectorProjectionSpec:
    embedding_model: str
    embedding_version: str
    index_schema_version: str

    def __post_init__(self) -> None:
        for field_name in (
            "embedding_model",
            "embedding_version",
            "index_schema_version",
        ):
            if not getattr(self, field_name).strip():
                raise InvalidInputError(f"{field_name} must not be blank.")
