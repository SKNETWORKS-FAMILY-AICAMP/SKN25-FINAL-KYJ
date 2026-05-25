from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select, Update

from foldmind_ai_core.adapters.outbound.postgres.models.folder_projections import (
    FolderIndexRecordRow,
)


class FolderIndexRecordStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_folder_index_record(
        self,
        row: FolderIndexRecordRow,
    ) -> None:
        await self.session.execute(_upsert_folder_index_record_statement(row))

    async def current_folder_signal_input_digest(
        self,
        *,
        folder_id: str,
    ) -> str | None:
        result = await self.session.execute(
            select(FolderIndexRecordRow.folder_signal_input_digest)
            .select_from(FolderIndexRecordRow)
            .where(FolderIndexRecordRow.folder_id == folder_id)
            .where(FolderIndexRecordRow.deleted_at.is_(None))
            .limit(1),
        )
        digest = result.scalar_one_or_none()
        if digest is None:
            return None
        return str(digest)

    async def current_folder_signal_generation_version(
        self,
        *,
        folder_id: str,
    ) -> str | None:
        result = await self.session.execute(
            select(FolderIndexRecordRow.signal_generation_version)
            .select_from(FolderIndexRecordRow)
            .where(FolderIndexRecordRow.folder_id == folder_id)
            .where(FolderIndexRecordRow.deleted_at.is_(None))
            .limit(1),
        )
        version = result.scalar_one_or_none()
        if version is None:
            return None
        return str(version)

    async def folder_index_input_digest_is_current(
        self,
        *,
        folder_id: str,
        folder_index_input_digest: str,
    ) -> bool:
        result = await self.session.execute(
            _current_folder_index_record_exists_query(
                folder_id=folder_id,
            ).where(
                FolderIndexRecordRow.folder_index_input_digest
                == folder_index_input_digest
            )
        )
        return result.scalar_one_or_none() is not None

    async def mark_folder_signals_pending(
        self,
        *,
        folder_id: str,
        folder_index_input_digest: str,
        folder_signal_input_digest: str,
    ) -> bool:
        result = await self.session.execute(
            _update_folder_index_record(folder_id=folder_id)
            .where(FolderIndexRecordRow.deleted_at.is_(None))
            .values(
                folder_index_input_digest=folder_index_input_digest,
                folder_signal_input_digest=folder_signal_input_digest,
                folder_signal_refresh_status="pending",
                updated_at=func.now(),
            )
            .returning(FolderIndexRecordRow.folder_id),
        )
        return result.scalar_one_or_none() is not None

    async def mark_folder_signals_ready(
        self,
        *,
        folder_id: str,
        folder_signal_input_digest: str,
        signal_generation_version: str,
    ) -> bool:
        result = await self.session.execute(
            _update_folder_index_record(folder_id=folder_id)
            .where(
                FolderIndexRecordRow.folder_signal_input_digest
                == folder_signal_input_digest
            )
            .where(FolderIndexRecordRow.deleted_at.is_(None))
            .values(
                folder_signal_refresh_status="ready",
                signal_generation_version=signal_generation_version,
                updated_at=func.now(),
            )
            .returning(FolderIndexRecordRow.folder_signal_input_digest),
        )
        return result.scalar_one_or_none() is not None

    async def mark_folder_index_deleted(
        self,
        *,
        folder_id: str,
        purge_after: datetime,
    ) -> None:
        await self.session.execute(
            _update_folder_index_record(folder_id=folder_id).values(
                deleted_at=func.coalesce(
                    FolderIndexRecordRow.deleted_at,
                    func.now(),
                ),
                purge_after=func.coalesce(
                    FolderIndexRecordRow.purge_after,
                    purge_after,
                ),
                updated_at=func.now(),
            )
        )


def _current_folder_index_record_exists_query(
    *,
    folder_id: str,
) -> Select[tuple[int]]:
    return (
        select(1)
        .select_from(FolderIndexRecordRow)
        .where(FolderIndexRecordRow.folder_id == folder_id)
        .where(FolderIndexRecordRow.deleted_at.is_(None))
        .limit(1)
    )


def _update_folder_index_record(*, folder_id: str) -> Update:
    return (
        update(FolderIndexRecordRow)
        .where(FolderIndexRecordRow.folder_id == folder_id)
    )


def _upsert_folder_index_record_statement(row: FolderIndexRecordRow) -> Insert:
    statement = insert(FolderIndexRecordRow).values(
        folder_id=row.folder_id,
        folder_index_input_digest=row.folder_index_input_digest,
        folder_signal_input_digest=row.folder_signal_input_digest,
        signal_generation_version=row.signal_generation_version,
        folder_signal_refresh_status=row.folder_signal_refresh_status,
        deleted_at=None,
        purge_after=None,
        updated_at=func.now(),
    )
    excluded = statement.excluded
    return statement.on_conflict_do_update(
        index_elements=[FolderIndexRecordRow.folder_id],
        set_={
            "folder_index_input_digest": excluded.folder_index_input_digest,
            "folder_signal_input_digest": excluded.folder_signal_input_digest,
            "signal_generation_version": excluded.signal_generation_version,
            "folder_signal_refresh_status": excluded.folder_signal_refresh_status,
            "deleted_at": None,
            "purge_after": None,
            "updated_at": func.now(),
        },
    )
