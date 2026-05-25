from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

DEFAULT_PURGE_AFTER_DAYS = 90


@dataclass(frozen=True, slots=True)
class PurgeAfterPolicy:
    days: int = DEFAULT_PURGE_AFTER_DAYS

    def purge_after(self) -> datetime:
        return datetime.now(UTC) + timedelta(days=self.days)
