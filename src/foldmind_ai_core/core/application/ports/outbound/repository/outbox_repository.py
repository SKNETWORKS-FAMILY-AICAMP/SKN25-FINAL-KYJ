from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.domain.models.outbox import OutboxEvent


class OutboxRepositoryPort(Protocol):
    async def append(self, event: OutboxEvent) -> None:
        ...
