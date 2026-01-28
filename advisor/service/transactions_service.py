import datetime
import logging
from asyncio import create_task, gather

from sqlalchemy import select

from advisor.db import db_models
from advisor.db.db_async_connector import DBAsyncConnector
from advisor.llm.llm_service import LLMService
from advisor.data_models import (
    CategorizationResultModel,
    NormalizedTransactionModel,
    RawTransactionModel,
    RecurrenceStatus,
)
from advisor.service.category_service import CategoryService

logger = logging.getLogger(__name__)


class TransactionsService:

    def __init__(self, llm_service: LLMService, category_service: CategoryService, db_connector: DBAsyncConnector):
        self.llm_service = llm_service
        self.category_service = category_service
        self.db_connector = db_connector

    async def get_user_raw_transactions(
        self,
        user_id: int,
    ) -> list[db_models.RawTransaction]:

        async with self.db_connector.get_session() as session:
            raw_result = await session.execute(
                select(db_models.RawTransaction)
                .outerjoin(db_models.NormalizedTransaction)
                .where(db_models.RawTransaction.user_id == user_id, db_models.NormalizedTransaction.id.is_(None))
            )
            return list(raw_result.scalars().all())

    async def normalize_and_categorize_raw_transactions(self, user_id: int) -> int:
        raw_transactions = await self.get_user_raw_transactions(user_id)

        if not raw_transactions:
            logger.info(f"All transactions for user {user_id} were normalized and categorized")
            return 0

        categories = await self.category_service.get_user_categories(user_id=user_id, global_fallback=True)

        categorized_transactions = []
        try:
            tasks = []
            for raw_db_transaction in raw_transactions:
                tasks.append(
                    create_task(self.normalize_and_categorize_single_transaction(raw_db_transaction, categories))
                )

            task_results = await gather(*tasks, return_exceptions=True)
            for task_result in task_results:
                if isinstance(task_result, Exception):
                    logger.exception("Categorization failed", exc_info=task_result)
                    continue
                categorized_transactions.append(self.map_normalized_transaction_to_db_model(task_result))  # type: ignore

        except Exception:
            logger.exception("Exception occurred during transactions normalization and categorization")

        async with self.db_connector.get_session() as session, session.begin():
            session.add_all(categorized_transactions)

        return len(categorized_transactions)

    async def normalize_and_categorize_single_transaction(
        self, raw_transaction: db_models.RawTransaction, categories: list[str]
    ) -> NormalizedTransactionModel:
        raw_transaction_model = self.map_raw_db_transaction_to_pydantic_model(raw_transaction)

        normalized_transaction = await self._normalize_transaction(raw_transaction_model)
        categorized_transaction = await self._categorize_transaction(normalized_transaction, categories)

        categorized_transaction.raw_transaction_id = raw_transaction.id
        categorized_transaction.user_id = raw_transaction.user_id
        return categorized_transaction

    async def _normalize_transaction(self, raw_transaction: RawTransactionModel) -> RawTransactionModel:
        return await self.llm_service.invoke_structured(
            prompt_key="normalize_transaction_user",
            variables={"transaction": raw_transaction.model_dump()},
            response_model=RawTransactionModel,
            system_prompt_key="normalize_transaction_system",
        )

    async def _categorize_transaction(
        self, raw_transaction: RawTransactionModel, categories: list[str]
    ) -> NormalizedTransactionModel:
        categorization_result = await self.llm_service.invoke_structured(
            prompt_key="categorize_transaction_user",
            variables={"transaction": raw_transaction.model_dump(), "user_categories": categories},
            response_model=CategorizationResultModel,
            system_prompt_key="categorize_transaction_system",
        )

        return NormalizedTransactionModel(
            type=raw_transaction.type,
            amount=raw_transaction.amount if raw_transaction.amount is not None else 0.0,
            date=raw_transaction.date if raw_transaction.date is not None else datetime.date.today(),
            currency=raw_transaction.currency if raw_transaction.currency is not None else "USD",
            description=raw_transaction.description,
            source=raw_transaction.source,
            raw_category=raw_transaction.raw_category if raw_transaction.raw_category is not None else "",
            predicted_category=categorization_result.predicted_category,
            category_confidence=categorization_result.category_confidence,
            resolved_category=categorization_result.predicted_category,
            recurrence_status=RecurrenceStatus.UNKNOWN,
            recurrence_confidence=0.0,
            recurrence_period=None,
        )

    @staticmethod
    def map_raw_db_transaction_to_pydantic_model(raw_db_transaction: db_models.RawTransaction) -> RawTransactionModel:
        return RawTransactionModel(**raw_db_transaction.to_dict())

    @staticmethod
    def map_normalized_transaction_to_db_model(
        normalized_db_model: NormalizedTransactionModel,
    ) -> db_models.NormalizedTransaction:
        return db_models.NormalizedTransaction(**normalized_db_model.model_dump())
