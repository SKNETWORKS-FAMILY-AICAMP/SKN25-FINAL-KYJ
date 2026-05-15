from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from neo4j import GraphDatabase

from foldmind_ai_core.adapters.outbound.neo4j.schema import ensure_schema as run_ensure_schema
from foldmind_ai_core.adapters.outbound.neo4j.settings import Neo4jSettings


@dataclass(slots=True)
class Neo4jClient:
    settings: Neo4jSettings
    driver: Any | None = None
    _driver: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._driver = self.driver or GraphDatabase.driver(
            self.settings.uri,
            auth=(self.settings.username, self.settings.password),
        )

    def session(self) -> Any:
        if self.settings.database:
            return self._driver.session(database=self.settings.database)
        return self._driver.session()

    def ensure_database_schema(self) -> None:
        with self.session() as session:
            run_ensure_schema(session)
