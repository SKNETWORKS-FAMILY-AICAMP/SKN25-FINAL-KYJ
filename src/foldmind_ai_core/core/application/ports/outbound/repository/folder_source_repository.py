from __future__ import annotations

from datetime import datetime
from typing import Protocol

from foldmind_ai_core.core.domain.models.folder_sources import (
    FolderSourceIdentity,
    SourceFolder,
)

FolderSourceKeywordMatch = tuple[SourceFolder, float]


class FolderSourceRepositoryPort(Protocol):
    async def upsert_folder_source(self, folder: SourceFolder) -> bool:
        ...

    async def get_current_folder_source(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> SourceFolder | None:
        ...

    async def ancestor_folder_ids(
        self,
        *,
        tenant: str,
        folder_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        ...

    async def active_folder_ids_in_subtree(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> tuple[str, ...]:
        ...

    async def folder_identity_for_delete(
        self,
        folder_id: str,
    ) -> FolderSourceIdentity | None:
        ...

    async def mark_folder_source_deleted(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> None:
        ...

    async def search_names_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        folder_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
    ) -> tuple[FolderSourceKeywordMatch, ...]:
        ...

    async def search_descriptions_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        folder_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
    ) -> tuple[FolderSourceKeywordMatch, ...]:
        ...
