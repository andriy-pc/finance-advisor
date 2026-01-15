from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from advisor.db.db_async_connector import DBAsyncConnector
from advisor.settings import ProjectSettings

db_connector: DBAsyncConnector | None = None
settings: ProjectSettings | None = None


def get_project_settings() -> ProjectSettings:
    global settings

    if settings is None:
        settings = ProjectSettings()
    return settings


def get_db_connector() -> DBAsyncConnector:
    global db_connector

    if db_connector is None:
        url = get_project_settings().sql_connection_url
        if not url:
            raise ValueError("sql_connection_url is not set")
        db_connector = DBAsyncConnector(url)
    return db_connector


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_db_connector().get_session() as session:
        yield session
