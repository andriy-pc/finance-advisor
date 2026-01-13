from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from advisor.dependencies import get_db_connector


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    db_connector = get_db_connector()
    async with db_connector.generate_engine():
        yield
