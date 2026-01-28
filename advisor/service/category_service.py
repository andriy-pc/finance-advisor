from sqlalchemy import select

from advisor.db.db_async_connector import DBAsyncConnector
from advisor.db.db_models import Category, GlobalCategory


class CategoryService:

    def __init__(self, db_connector: DBAsyncConnector):
        self.db_connector = db_connector

    async def get_user_categories(self, user_id: int, global_fallback: bool) -> list[str]:

        async with self.db_connector.get_session() as session:
            categories = list(
                (await session.execute(select(Category.name).where(Category.user_id == user_id))).scalars()
            )

            if not categories and global_fallback:
                return list((await session.execute(select(GlobalCategory.name))).scalars())

            return categories
