from sqlalchemy import select

from advisor.db.db_async_connector import DBAsyncConnector
from advisor.db.db_models import Category


class UsersService:

    def __init__(self, db_connector: DBAsyncConnector):
        self.db_connector = db_connector

    async def get_categories(self, user_id: int) -> list[Category]:
        async with self.db_connector.get_session() as session:
            return list((await session.execute(select(Category).where(Category.user_id == user_id))).scalars())

    async def get_default_currency(self) -> str:
        # TODO: ! implement
        return "USD"
