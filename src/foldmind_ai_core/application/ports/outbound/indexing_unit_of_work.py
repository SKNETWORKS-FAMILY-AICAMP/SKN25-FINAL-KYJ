from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Protocol

from foldmind_ai_core.domain.indexing.outbox import OutboxEvent
from foldmind_ai_core.domain.profiling.models import DocumentProfile


class IndexingTransaction(Protocol):
    def upsert_document_profile(self, profile: DocumentProfile) -> None:
        ...

    def delete_document_profile(self, *, document_id: str) -> None:
        ...

    def append_outbox_event(self, event: OutboxEvent) -> None:
        ...


class IndexingUnitOfWork(Protocol):
    def transaction(self) -> AbstractContextManager[IndexingTransaction]:
        ...
