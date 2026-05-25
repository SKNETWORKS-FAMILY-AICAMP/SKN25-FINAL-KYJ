from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings
from foldmind_ai_core.core.application.errors import DatabaseError


class PostgresSessionProvider(Protocol):
    def session(self) -> AbstractAsyncContextManager[AsyncSession]: ...

    def transaction(self) -> AbstractAsyncContextManager[AsyncSession]: ...


@dataclass(slots=True)
class PostgresClient:
    settings: PostgresSettings
    _engine: AsyncEngine | None = field(default=None, init=False, repr=False)
    _instrumented: bool = field(default=False, init=False, repr=False)
    _sessionmaker: async_sessionmaker[AsyncSession] | None = field(
        default=None,
        init=False,
        repr=False,
    )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        try:
            async with self._sessions()() as session:
                yield session
        except SQLAlchemyError as exc:
            raise DatabaseError("Postgres session failed.") from exc

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        try:
            async with self._sessions()() as session:
                async with session.begin():
                    yield session
        except SQLAlchemyError as exc:
            raise DatabaseError("Postgres transaction failed.") from exc

    def _sessions(self) -> async_sessionmaker[AsyncSession]:
        if self._sessionmaker is None:
            self._sessionmaker = async_sessionmaker(
                self._engine_for_sessions(),
                expire_on_commit=False,
            )
        return self._sessionmaker

    async def close(self) -> None:
        if self._engine is None:
            return
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None
        self._instrumented = False

    def _engine_for_sessions(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(_sqlalchemy_asyncpg_dsn(self.settings.dsn))
            self._instrument_engine()
        return self._engine

    def _instrument_engine(self) -> None:
        if self._engine is None or self._instrumented:
            return
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(engine=self._engine.sync_engine)
        self._instrumented = True


def _sqlalchemy_asyncpg_dsn(dsn: str) -> str:
    if dsn.startswith("postgresql+asyncpg://"):
        return dsn
    if dsn.startswith("postgresql://"):
        return f"postgresql+asyncpg://{dsn.removeprefix('postgresql://')}"
    if dsn.startswith("postgres://"):
        return f"postgresql+asyncpg://{dsn.removeprefix('postgres://')}"
    return dsn
