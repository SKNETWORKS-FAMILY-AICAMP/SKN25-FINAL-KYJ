from __future__ import annotations

from types import TracebackType
from typing import Protocol

from ..repository.document_projection_repository import (
    DocumentProjectionRepositoryPort,
)
from ..repository.document_relation_repository import (
    DocumentRelationRepositoryPort,
)
from ..repository.document_source_repository import (
    DocumentSourceRepositoryPort,
)
from ..repository.folder_projection_repository import (
    FolderProjectionRepositoryPort,
)
from ..repository.folder_source_repository import (
    FolderSourceRepositoryPort,
)
from ..repository.outbox_repository import OutboxRepositoryPort


class IndexingWriteSession(Protocol):
    document_sources: DocumentSourceRepositoryPort
    folder_sources: FolderSourceRepositoryPort
    document_projections: DocumentProjectionRepositoryPort
    document_relations: DocumentRelationRepositoryPort
    folder_projections: FolderProjectionRepositoryPort
    outbox: OutboxRepositoryPort


class IndexingWriteSessionScope(Protocol):
    async def __aenter__(self) -> IndexingWriteSession:
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        ...


class IndexingWriteSessionProvider(Protocol):
    def transaction(self) -> IndexingWriteSessionScope:
        ...
