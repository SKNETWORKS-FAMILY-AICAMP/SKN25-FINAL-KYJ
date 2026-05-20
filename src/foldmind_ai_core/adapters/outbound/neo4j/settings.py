from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.shared.validation import require_non_blank


@dataclass(frozen=True, slots=True)
class Neo4jSettings:
    uri: str
    username: str
    password: str
    database: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "uri", require_non_blank(self.uri, "uri"))
        object.__setattr__(self, "username", require_non_blank(self.username, "username"))
        object.__setattr__(self, "password", require_non_blank(self.password, "password"))
        if self.database is not None:
            object.__setattr__(
                self,
                "database",
                require_non_blank(self.database, "database"),
            )
