from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class DBTestHelper:  # pragma: no cover
    """Used to generate in memory DB engine for a test environment."""

    def __init__(self):

        self._in_memory_async_engine = None
        self._in_memory_async_session = None

    @asynccontextmanager
    async def generate_in_memory_async_engine(
        self, orm_base: DeclarativeBase, remove_autoincrement: bool = False
    ) -> AsyncGenerator[None, None]:
        if remove_autoincrement:
            self._remove_autoincrement_from_metadata(orm_base.metadata)

        self._in_memory_async_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async with self._in_memory_async_engine.begin() as conn:
            await conn.run_sync(orm_base.metadata.create_all)

        self._in_memory_async_session = async_sessionmaker(self._in_memory_async_engine, expire_on_commit=False)

        # Drastically slows unit tests
        for table_name in orm_base.metadata.tables.keys():
            await self.alter_async_table_to_support_sqlite(table_name, self._in_memory_async_engine)

        try:
            yield
        finally:
            await self._in_memory_async_engine.dispose()

    async def alter_async_table_to_support_sqlite(
        self,
        table_name: str,
        _override_engine: AsyncEngine,
    ) -> None:
        metadata = MetaData()
        async with _override_engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: metadata.reflect(bind=sync_conn))
        if table_name in metadata.tables:
            if "id" in metadata.tables[table_name].columns:
                async with _override_engine.begin() as conn:
                    await conn.run_sync(metadata.tables[table_name].drop)

        # SQLite: if a column is INTEGER PRIMARY_KEY - then it is AUTO_INCREMENT
        if "id" in metadata.tables[table_name].columns:
            _ = Table(
                table_name,
                metadata,
                Column("id", Integer, primary_key=True),
                extend_existing=True,
            )
        async with _override_engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    @asynccontextmanager
    async def get_in_memory_async_session(self, *args, **kwargs) -> AsyncGenerator[AsyncSession, None]:
        async_session = self._in_memory_async_session()
        try:
            yield async_session
        finally:
            await async_session.close()

    def _remove_autoincrement_from_metadata(self, metadata: MetaData) -> None:
        """Remove autoincrement from all primary key columns to support SQLite composite keys."""
        for table in metadata.tables.values():
            for column in table.columns:
                if column.primary_key and column.autoincrement:
                    column.autoincrement = False
