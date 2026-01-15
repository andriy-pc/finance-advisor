import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from advisor.settings import SQLSettings

logger = logging.getLogger(__name__)


class DBAsyncConnector:
    _async_engine: AsyncEngine
    _async_session: "async_sessionmaker[AsyncSession]"

    def __init__(self, db_uri: str):
        self._db_uri = db_uri

    @asynccontextmanager
    async def generate_engine(
        self,
        custom_settings: SQLSettings | None = None,
    ) -> AsyncGenerator[None, None]:
        """Creates async engine.

        Usage:
        async with generate_async_engine():
            async with get_async_session() as session: ...
        """
        sql_settings = custom_settings or SQLSettings()
        logger.info("creating async engine")
        self._async_engine = create_async_engine(
            self._db_uri,
            connect_args={"server_settings": {"timezone": "UTC"}},
            pool_size=sql_settings.pool_size,
            max_overflow=sql_settings.max_overflow,
            pool_recycle=sql_settings.pool_recycle,
            echo=False,
        )
        self._async_session = async_sessionmaker(self._async_engine)
        try:
            yield
        finally:
            logger.info("disposing async engine")
            await self._async_engine.dispose()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Creates async session from sessionmaker.

        Requires engine context before usage:
        async with generate_async_engine():
            ...
            async with get_async_session() as session:
                ...

        To manage transaction - use context manager:
        async with get_session() as session, session.begin():
            ...

        At the end of the above context, assuming no exceptions were raised,
        any pending objects will be flushed to the database and the database transaction will be committed.
        """

        session = self._async_session()
        try:
            yield session
        finally:
            await session.close()


async def create_db_and_tables() -> None:
    from advisor.db.db_models import Base
    from advisor.dependencies import get_project_settings

    connector = DBAsyncConnector(get_project_settings().sql_connection_url or "")
    async with connector.generate_engine():
        async with connector._async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
