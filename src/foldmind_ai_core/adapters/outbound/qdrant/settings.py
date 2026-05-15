from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QdrantSettings:
    url: str | None = None
    api_key: str | None = None
