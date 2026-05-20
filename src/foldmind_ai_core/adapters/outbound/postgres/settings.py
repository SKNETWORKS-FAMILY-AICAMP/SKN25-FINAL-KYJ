from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.shared.validation import require_non_blank


@dataclass(frozen=True, slots=True)
class PostgresSettings:
    dsn: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "dsn", require_non_blank(self.dsn, "dsn"))
