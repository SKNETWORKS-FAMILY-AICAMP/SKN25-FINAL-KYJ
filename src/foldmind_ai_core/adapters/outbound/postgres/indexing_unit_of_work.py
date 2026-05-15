from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient
from foldmind_ai_core.adapters.outbound.postgres.outbox_repository import (
    PostgresOutboxRepository,
)
from foldmind_ai_core.adapters.outbound.postgres.profile_repository import (
    PostgresProfileRepository,
)
from foldmind_ai_core.domain.indexing.outbox import OutboxEvent
from foldmind_ai_core.domain.profiling.models import DocumentProfile


@dataclass(slots=True)
class PostgresIndexingUnitOfWork:
    client: PostgresClient
    profile_repository: PostgresProfileRepository
    outbox_repository: PostgresOutboxRepository

    @contextmanager
    def transaction(self) -> Iterator[PostgresIndexingTransaction]:
        with self.client.transaction() as conn:
            yield PostgresIndexingTransaction(
                conn=conn,
                profile_repository=self.profile_repository,
                outbox_repository=self.outbox_repository,
            )


@dataclass(slots=True)
class PostgresIndexingTransaction:
    conn: Any
    profile_repository: PostgresProfileRepository
    outbox_repository: PostgresOutboxRepository

    def upsert_document_profile(self, profile: DocumentProfile) -> None:
        self.profile_repository.upsert_with_connection(self.conn, profile)

    def delete_document_profile(self, *, document_id: str) -> None:
        self.profile_repository.delete_with_connection(self.conn, document_id=document_id)

    def append_outbox_event(self, event: OutboxEvent) -> None:
        self.outbox_repository.append_with_connection(self.conn, event)
