from typing import Any, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from advisor.db.db_models import Category, Transaction
from advisor.dependencies import get_db_connector, get_session
from advisor.llm.llm_client import AdvisorLLMClient
from advisor.llm.ollama_provider import LLMFactory


class CategorizationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        # Initialize the generic provider
        provider = LLMFactory.get_provider("ollama")
        # Pass it to our domain client
        self.llm = AdvisorLLMClient(provider)

    async def get_all_categories(self) -> List[str]:
        stmt = select(Category.name)
        result = await self.db.scalars(stmt)
        return list(result.all())

    async def ensure_default_categories(self) -> None:
        existing_list = await self.get_all_categories()
        existing = set(existing_list)

        defaults = [
            "Housing",
            "Transportation",
            "Food",
            "Utilities",
            "Clothing",
            "Medical/Healthcare",
            "Gifts/Donations",
            "Entertainment",
            "Personal",
        ]

        for name in defaults:
            if name not in existing:
                self.db.add(Category(name=name, is_discretionary=True))
        await self.db.commit()

    async def categorize_transaction_background(self, transaction_ids: List[str]) -> None:
        """
        Intended to be run as a background task.
        Fetches transactions, asks LLM for category, updates DB.
        """
        # Use the context manager pattern as requested
        async with get_session() as session, session.begin():
            # We need a service instance attached to this new session
            service_with_new_session = CategorizationService(session)

            categories = await service_with_new_session.get_all_categories()
            if not categories:
                await service_with_new_session.ensure_default_categories()
                categories = await service_with_new_session.get_all_categories()

            stmt = select(Transaction).where(Transaction.external_id.in_(transaction_ids))
            result = await session.scalars(stmt)
            transactions = result.all()

            for txn in transactions:
                if txn.category_id is None:  # Only categorize if missing
                    predicted_category_name = await self.llm.predict_category(txn.description, categories)

                    # Find category ID
                    cat_stmt = select(Category).where(Category.name == predicted_category_name)
                    cat_result = await session.scalars(cat_stmt)
                    category = cat_result.first()

                    if category:
                        txn.category = category


class FinancialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_spending_by_category(self) -> Any:
        # Example aggregation
        stmt = (
            select(Category.name, func.sum(Transaction.amount))
            .join(Category, Transaction.category_id == Category.id)
            .group_by(Category.name)
        )
        result = await self.db.execute(stmt)
        return result.all()
