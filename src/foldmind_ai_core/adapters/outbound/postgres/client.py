from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings
from foldmind_ai_core.shared.types import JsonValue


@dataclass(slots=True)
class PostgresClient:
    settings: PostgresSettings
    connection: Any | None = None

    @contextmanager
    def connect(self) -> Iterator[Any]:
        if self.connection is not None:
            yield self.connection
            return
        with psycopg.connect(self.settings.dsn) as conn:
            yield conn

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        with self.connect() as conn:
            transaction = getattr(conn, "transaction", None)
            if callable(transaction):
                with transaction():
                    yield conn
                return
            yield conn


def jsonb(value: JsonValue) -> Any:
    return Jsonb(value)


def row_value(row: Any, key: str, index: int = 0) -> Any:
    if isinstance(row, dict):
        if key in row:
            return row[key]
        return list(row.values())[index]
    return row[index]
