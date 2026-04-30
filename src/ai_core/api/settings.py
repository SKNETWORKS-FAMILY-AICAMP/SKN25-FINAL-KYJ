from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_csv(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _clean_origins(values: Sequence[object]) -> tuple[str, ...]:
    origins: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError("cors_origins entries must be strings.")
        if stripped := value.strip():
            origins.append(stripped)
    return tuple(origins)


def _parse_cors_origins(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ()
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            if not isinstance(parsed, list):
                raise TypeError("cors_origins JSON value must be a list of strings.")
            return _clean_origins(parsed)
        return _split_csv(stripped)

    if isinstance(value, Sequence):
        return _clean_origins(value)

    raise TypeError("cors_origins must be a string or sequence of strings.")


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(extra="forbid", populate_by_name=True)

    title: str = Field(default="FoldMind AI Core", validation_alias="FOLDMIND_API_TITLE")
    version: str = Field(default="0.1.0", validation_alias="FOLDMIND_API_VERSION")
    cors_origins: Annotated[tuple[str, ...], NoDecode] = Field(
        default_factory=tuple,
        validation_alias="FOLDMIND_CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        validation_alias="FOLDMIND_CORS_ALLOW_CREDENTIALS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> tuple[str, ...]:
        return _parse_cors_origins(value)

    @classmethod
    def from_env(cls) -> APISettings:
        return cls()
