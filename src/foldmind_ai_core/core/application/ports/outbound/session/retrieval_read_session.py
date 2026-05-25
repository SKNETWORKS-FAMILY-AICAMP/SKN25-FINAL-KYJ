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
from ..repository.folder_source_repository import (
    FolderSourceRepositoryPort,
)


class RetrievalReadSession(Protocol):
    document_sources: DocumentSourceRepositoryPort
    document_projections: DocumentProjectionRepositoryPort
    document_relations: DocumentRelationRepositoryPort
    folder_sources: FolderSourceRepositoryPort


class RetrievalReadSessionScope(Protocol):
    async def __aenter__(self) -> RetrievalReadSession:
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        ...


class RetrievalReadSessionProvider(Protocol):
    def session(self) -> RetrievalReadSessionScope:
        ...
