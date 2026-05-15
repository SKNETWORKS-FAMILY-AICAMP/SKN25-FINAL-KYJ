from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VectorProjectionSpec:
    embedding_model: str
    embedding_version: str
    index_schema_version: str
