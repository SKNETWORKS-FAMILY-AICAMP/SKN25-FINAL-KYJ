from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from neo4j import GraphDatabase

from foldmind_ai_core.adapters.outbound.neo4j.schema import ensure_neo4j_schema
from foldmind_ai_core.adapters.outbound.neo4j.settings import Neo4jSettings
from foldmind_ai_core.core.application.errors import ProviderCallError


@dataclass(slots=True)
class Neo4jClient:
    settings: Neo4jSettings
    driver: Any | None = None
    _driver: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            self._driver = self.driver or GraphDatabase.driver(
                self.settings.uri,
                auth=(self.settings.username, self.settings.password),
            )
        except Exception as exc:
            raise ProviderCallError("Neo4j driver setup failed.") from exc

    def session(self) -> Any:
        try:
            if self.settings.database:
                return self._driver.session(database=self.settings.database)
            return self._driver.session()
        except Exception as exc:
            raise ProviderCallError("Neo4j session creation failed.") from exc

    def ensure_database_schema(self) -> None:
        try:
            with self.session() as session:
                ensure_neo4j_schema(session)
        except ProviderCallError:
            raise
        except Exception as exc:
            raise ProviderCallError("Neo4j schema setup failed.") from exc

    def close(self) -> None:
        close = getattr(self._driver, "close", None)
        if close is not None:
            try:
                close()
            except Exception as exc:
                raise ProviderCallError("Neo4j driver close failed.") from exc
