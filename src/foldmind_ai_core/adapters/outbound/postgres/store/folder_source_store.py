from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from foldmind_ai_core.adapters.outbound.postgres.models.sources import FolderSourceRow

FolderKeywordRow = tuple[FolderSourceRow, float]


class FolderSourceStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_folder_source(self, row: FolderSourceRow) -> None:
        await self.session.execute(_upsert_folder_source_statement(row))

    async def folder_source_version_is_current(
        self,
        *,
        tenant: str,
        folder_id: str,
        source_version: str,
    ) -> bool:
        result = await self.session.execute(
            select(1)
            .select_from(FolderSourceRow)
            .where(FolderSourceRow.folder_id == folder_id)
            .where(FolderSourceRow.tenant_id == tenant)
            .where(FolderSourceRow.source_version == source_version)
            .where(FolderSourceRow.deleted_at.is_(None))
            .limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def folder_source_row_for_delete(
        self,
        folder_id: str,
    ) -> FolderSourceRow | None:
        result = await self.session.execute(
            select(FolderSourceRow)
            .where(FolderSourceRow.folder_id == folder_id)
            .where(FolderSourceRow.deleted_at.is_(None)),
        )
        return result.scalar_one_or_none()

    async def mark_folder_source_deleted(
        self,
        *,
        tenant: str,
        folder_id: str,
        purge_after: datetime,
    ) -> None:
        await self.session.execute(
            update(FolderSourceRow)
            .where(FolderSourceRow.tenant_id == tenant)
            .where(FolderSourceRow.folder_id == folder_id)
            .values(
                deleted_at=func.coalesce(FolderSourceRow.deleted_at, func.now()),
                purge_after=func.coalesce(
                    FolderSourceRow.purge_after,
                    purge_after,
                ),
                updated_at=func.now(),
            ),
        )

    async def current_folder_source_row(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> FolderSourceRow | None:
        result = await self.session.execute(
            select(FolderSourceRow)
            .where(FolderSourceRow.tenant_id == tenant)
            .where(FolderSourceRow.folder_id == folder_id)
            .where(FolderSourceRow.deleted_at.is_(None)),
        )
        return result.scalar_one_or_none()

    async def ancestor_folder_ids(
        self,
        *,
        tenant: str,
        folder_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        if not folder_ids:
            return ()

        ancestor_folders = (
            select(FolderSourceRow.folder_id, FolderSourceRow.parent_folder_id)
            .where(FolderSourceRow.tenant_id == tenant)
            .where(FolderSourceRow.folder_id.in_(folder_ids))
            .where(FolderSourceRow.deleted_at.is_(None))
            .cte("ancestor_folders", recursive=True)
        )
        parent = aliased(FolderSourceRow)
        ancestor_folders = ancestor_folders.union(
            select(parent.folder_id, parent.parent_folder_id)
            .join(
                ancestor_folders,
                parent.folder_id == ancestor_folders.c.parent_folder_id,
            )
            .where(parent.tenant_id == tenant)
            .where(parent.deleted_at.is_(None))
        )
        result = await self.session.execute(
            select(ancestor_folders.c.folder_id).order_by(ancestor_folders.c.folder_id)
        )
        return tuple(result.scalars().all())

    async def active_folder_ids_in_subtree(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> tuple[str, ...]:
        subtree_folders = (
            select(FolderSourceRow.folder_id)
            .where(FolderSourceRow.tenant_id == tenant)
            .where(FolderSourceRow.folder_id == folder_id)
            .where(FolderSourceRow.deleted_at.is_(None))
            .cte("subtree_folders", recursive=True)
        )
        child_folder = aliased(FolderSourceRow)
        subtree_folders = subtree_folders.union(
            select(child_folder.folder_id)
            .join(
                subtree_folders,
                child_folder.parent_folder_id == subtree_folders.c.folder_id,
            )
            .where(child_folder.tenant_id == tenant)
            .where(child_folder.deleted_at.is_(None))
        )
        result = await self.session.execute(
            select(subtree_folders.c.folder_id).order_by(subtree_folders.c.folder_id)
        )
        return tuple(result.scalars().all())

    async def keyword_name_rows(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        folder_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
    ) -> list[FolderKeywordRow]:
        search_query = func.plainto_tsquery("simple", query_text)
        score = func.ts_rank_cd(FolderSourceRow.name_search_vector, search_query)
        conditions: list[object] = []
        if folder_ids:
            conditions.append(FolderSourceRow.folder_id.in_(folder_ids))
        if created_at is not None:
            conditions.append(FolderSourceRow.source_created_at == created_at)
        if updated_at is not None:
            conditions.append(FolderSourceRow.source_updated_at == updated_at)

        result = await self.session.execute(
            select(FolderSourceRow, score)
            .where(FolderSourceRow.tenant_id == tenant)
            .where(FolderSourceRow.deleted_at.is_(None))
            .where(FolderSourceRow.name_search_vector.op("@@")(search_query))
            .where(*conditions)
            .order_by(score.desc(), FolderSourceRow.source_updated_at.desc())
            .limit(top_k)
        )
        return [(folder_row, float(row_score)) for folder_row, row_score in result.all()]

    async def keyword_description_rows(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        folder_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
    ) -> list[FolderKeywordRow]:
        search_query = func.plainto_tsquery("simple", query_text)
        score = func.ts_rank_cd(
            FolderSourceRow.description_search_vector,
            search_query,
        )
        conditions: list[object] = []
        if folder_ids:
            conditions.append(FolderSourceRow.folder_id.in_(folder_ids))
        if created_at is not None:
            conditions.append(FolderSourceRow.source_created_at == created_at)
        if updated_at is not None:
            conditions.append(FolderSourceRow.source_updated_at == updated_at)

        result = await self.session.execute(
            select(FolderSourceRow, score)
            .where(FolderSourceRow.tenant_id == tenant)
            .where(FolderSourceRow.deleted_at.is_(None))
            .where(FolderSourceRow.description_search_vector.op("@@")(search_query))
            .where(*conditions)
            .order_by(score.desc(), FolderSourceRow.source_updated_at.desc())
            .limit(top_k)
        )
        return [(folder_row, float(row_score)) for folder_row, row_score in result.all()]


def _upsert_folder_source_statement(row: FolderSourceRow) -> Insert:
    statement = insert(FolderSourceRow).values(
        folder_id=row.folder_id,
        tenant_id=row.tenant_id,
        source_version=row.source_version,
        source_created_at=row.source_created_at,
        source_updated_at=row.source_updated_at,
        name=row.name,
        path=row.path,
        parent_folder_id=row.parent_folder_id,
        description=row.description,
        metadata_json=row.metadata_json,
        updated_at=func.now(),
    )
    excluded = statement.excluded
    current_or_newer_source = (
        (FolderSourceRow.source_version == excluded.source_version)
        | (FolderSourceRow.source_updated_at < excluded.source_updated_at)
    )
    return statement.on_conflict_do_update(
        index_elements=[FolderSourceRow.folder_id],
        set_={
            "tenant_id": excluded.tenant_id,
            "source_version": excluded.source_version,
            "source_created_at": excluded.source_created_at,
            "source_updated_at": excluded.source_updated_at,
            "name": excluded.name,
            "path": excluded.path,
            "parent_folder_id": excluded.parent_folder_id,
            "description": excluded.description,
            "metadata_json": excluded.metadata_json,
            "deleted_at": None,
            "purge_after": None,
            "updated_at": func.now(),
        },
        where=current_or_newer_source,
    )
