from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Neo4jSettings:
    uri: str
    username: str
    password: str
    database: str | None = None
